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
    print("  RUANG VISUAL — Market Intelligence Pipeline")
    print("  Makassar, Sulawesi Selatan")
    print("=" * 60)


def print_help():
    print_banner()
    print()
    print("Cara pakai:")
    print("  python run_pipeline.py <module> [options]")
    print()
    print("Modules yang tersedia:")
    print("  all            Jalankan SELURUH pipeline & kirim rekap ke Telegram (Mode Cloud)")
    print("  gmaps          Google Maps scraper — Leads, Competitors & Trends (Module B)")
    print("  facebook       Facebook Marketplace Makassar — Leads, Competitors & Trends")
    print("  instagram      Instagram Intelligence Scraper — Leads, Competitors & Trends (Module C)")
    print("  tiktok         TikTok Intelligence Engine — Leads, Competitors & Trends (Module D)")
    print("  threads        Threads Intelligence Scraper — Leads, Competitors & Trends")
    print("  matrix         Competitor Intelligence & Strategy Matrix (Module F)")
    print("  clean-sheets   Bersihkan baris data uji coba di 3 tab utama Google Sheets")
    print("  bot            Jalankan Telegram Bot Listener langsung di terminal")
    print("  export-csv     Ekspor seluruh data terbaru ke format CSV")
    print("  enrich-web     Pengayaan kontak WhatsApp dari website/bio link calon customer")
    print("  init-sheets    Inisialisasi/update Google Sheets")
    print()
    print("Contoh:")
    print("  python run_pipeline.py all --limit 2 --notify-telegram")
    print("  python run_pipeline.py facebook --mode all")
    print("  python run_pipeline.py gmaps --mode leads --limit 3 --dry-run")
    print("  python run_pipeline.py instagram --mode all --dry-run")
    print("  python run_pipeline.py tiktok --mode all --dry-run")
    print("  python run_pipeline.py threads --mode all --dry-run")
    print("  python run_pipeline.py matrix --dry-run")
    print("  python run_pipeline.py clean-sheets")
    print()


def run_gmaps():
    """Jalankan Google Maps scraper."""
    from scrapers.gmaps_scraper import main
    main()


def run_init_sheets():
    """Inisialisasi Google Sheets dengan tab baru jika perlu."""
    from scrapers.utils import get_logger, build_sheets_service, get_spreadsheet_id, append_rows_to_sheet

    log = get_logger("init")
    log.info("Menginisialisasi Google Sheets...")

    service = build_sheets_service()
    spreadsheet_id = get_spreadsheet_id()

    # Ambil sheets yang ada
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing = [s["properties"]["title"] for s in meta.get("sheets", [])]
    log.info(f"Sheets yang ada: {existing}")

    # Sheets yang dibutuhkan sesuai PRD §12
    required_sheets = {
        "Radar Prospek": [
            "Nama Bisnis", "Kategori", "Sumber Platform", "Skor", "Status", "No. WhatsApp",
            "Link WA", "Proyeksi Kebutuhan Cetak", "Pemicu Kebutuhan & Konteks", "Alamat",
            "Rating & Ulasan", "Website", "Link Sumber Asli", "Tanggal"
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
            log.info(f"  Membuat tab: '{title}'")
            requests.append({"addSheet": {"properties": {"title": title}}})

    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()
        log.info("  Tab baru berhasil dibuat.")

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
            log.info(f"  Header ditulis untuk '{title}'")
        else:
            log.info(f"  Header '{title}' sudah ada")

    log.info("\nInisialisasi selesai.")


def run_matrix():
    """Jalankan Competitor Matrix Analyzer."""
    from scrapers.competitor_analyzer import main as matrix_main
    matrix_main()


def run_instagram():
    """Jalankan Instagram scraper."""
    from scrapers.instagram_scraper import main as ig_main
    ig_main()


def run_tiktok():
    """Jalankan TikTok Intelligence Engine."""
    from scrapers.tiktok_scraper import main as tiktok_main
    tiktok_main()


def run_facebook():
    """Jalankan Facebook Marketplace Scraper."""
    from scrapers.facebook_marketplace_scraper import main as fb_main
    fb_main()


def run_threads():
    """Jalankan Threads Intelligence Scraper."""
    from scrapers.threads_scraper import main as threads_main
    threads_main()


def run_food():
    """Jalankan GoFood/GrabFood Merchant Scraper untuk sektor kuliner Makassar."""
    from scrapers.food_delivery_scraper import main as food_main
    food_main()


def run_clean_sheets():
    """Kirim perintah pembersihan data uji coba ke 3 tab utama Google Sheets."""
    from scrapers.utils import get_logger, append_rows_to_sheet
    log = get_logger("clean-sheets")
    log.info("Mengirim sinyal pembersihan ke Google Sheets...")
    try:
        append_rows_to_sheet("Radar Prospek", [], action="clear_all_sheets")
        log.info("Google Sheets berhasil dibersihkan. Hanya 3 tab utama dengan header terformat rapi yang dipertahankan.")
    except Exception as e:
        log.error(f"Gagal membersihkan Google Sheets: {e}")


def run_dedup():
    """Jalankan Lead Deduplication Engine untuk menganalisis data prospek lokal."""
    from scrapers.utils import get_logger, deduplicate_leads, PROCESSED_DIR
    log = get_logger("dedup-runner")
    leads_files = sorted(PROCESSED_DIR.glob("leads_scored_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not leads_files:
        log.info("Tidak ada file riwayat prospek di data/processed/")
        return
    with open(leads_files[0], "r", encoding="utf-8") as f:
        leads = json.load(f)
    log.info(f"Menganalisis file terbaru: {leads_files[0].name} ({len(leads)} leads)...")
    clean, dups = deduplicate_leads(leads)
    log.info(f"Hasil deduplikasi: {len(clean)} prospek unik/bersih, {dups} prospek terdeteksi duplikat.")


def run_telegram_bot():
    """Jalankan Telegram Bot polling runner."""
    from scrapers.telegram_bot import main as bot_main
    bot_main()


def run_export_csv():
    """Ekspor seluruh data terbaru di data/processed ke file CSV yang siap dibuka di Excel/Numbers."""
    import csv
    from scrapers.utils import get_logger
    log = get_logger("export-csv")
    proc_dir = Path("data/processed")

    # 1. Leads to CSV (Termasuk Segmentasi WhatsApp Ready vs Telepon Kantor)
    from scrapers.contact_enricher import classify_phone_number, enrich_lead_record
    leads_files = sorted(proc_dir.glob("leads_scored_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if leads_files:
        with open(leads_files[0], "r", encoding="utf-8") as f:
            leads = json.load(f)

        csv_all = proc_dir / "leads_calon_customer.csv"
        csv_wa = proc_dir / "leads_whatsapp_ready.csv"
        csv_office = proc_dir / "leads_telepon_kantor.csv"
        csv_no_phone = proc_dir / "leads_butuh_pengayaan.csv"

        headers = [
            "Nama Bisnis", "Kategori", "Sumber Platform", "Skor", "Status", "No. WhatsApp",
            "Link WA", "Tipe Kontak", "Klaster Wilayah", "Tier Bisnis",
            "Proyeksi Kebutuhan Cetak", "Pemicu & Konteks", "Alamat", "Rating & Ulasan",
            "Website", "Link Sumber Asli", "Tanggal"
        ]

        rows_all = []
        rows_wa = []
        rows_office = []
        rows_no_phone = []

        for l in leads:
            l = enrich_lead_record(l)
            phone_info = classify_phone_number(l.get("telepon", ""))
            phone_display = phone_info["formatted"]
            wa_url = l.get("whatsapp_link") or (f"https://wa.me/{phone_info['clean_number']}" if phone_info["is_wa_ready"] else "-")
            rating_str = f"{l.get('rating', 0)} ({l.get('jumlah_review', 0)} ulasan)"
            platform = l.get("platform_sumber", "Google Maps")
            pemicu = l.get("pemicu_kebutuhan", "-")
            source_url = l.get("url_sumber", "") or l.get("url_gmaps", "-")

            row = [
                l.get("nama_bisnis", ""),
                l.get("kategori", "Umum").upper(),
                platform,
                l.get("skor", 7),
                l.get("skor_label", "WARM"),
                phone_display,
                wa_url,
                phone_info["label"],
                l.get("klaster_wilayah", "Makassar"),
                l.get("tier_bisnis", "Tier 2"),
                l.get("proyeksi_kebutuhan", "Banner dan Media Promosi"),
                pemicu,
                l.get("alamat", "-") or "-",
                rating_str,
                l.get("website", "-") or "-",
                source_url,
                l.get("scrape_date", ""),
            ]

            rows_all.append(row)
            if phone_info["is_wa_ready"]:
                rows_wa.append(row)
            elif phone_info["type"] == "landline":
                rows_office.append(row)
            else:
                rows_no_phone.append(row)

        for filepath, data_rows in [
            (csv_all, rows_all),
            (csv_wa, rows_wa),
            (csv_office, rows_office),
            (csv_no_phone, rows_no_phone),
        ]:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(headers)
                w.writerows(data_rows)

        log.info(f"Leads diekspor: {len(rows_all)} total, {len(rows_wa)} WhatsApp Ready, {len(rows_office)} Telepon Kantor, {len(rows_no_phone)} Butuh Pengayaan")

    # 2. Competitor Matrix to CSV
    matrix_files = sorted(proc_dir.glob("competitor_matrix_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if matrix_files:
        with open(matrix_files[0], "r", encoding="utf-8") as f:
            matrix = json.load(f)
        csv_file = proc_dir / "matriks_kompetitor.csv"
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([
                "Nama Percetakan", "Fokus Layanan Utama", "Kapasitas / Skala",
                "Rating & Ulasan", "No. WhatsApp", "Link WA", "Celah Kualitas",
                "Celah Pelayanan & SOP", "Selling Point RUANG VISUAL", "Website / Maps", "Tanggal Update"
            ])
            for m in matrix:
                phone = m.get("telepon", "").strip()
                clean_phone = "".join([c for c in phone if c.isdigit()])
                if clean_phone.startswith("08"):
                    clean_phone = "62" + clean_phone[1:]
                elif clean_phone.startswith("8"):
                    clean_phone = "62" + clean_phone
                wa_link = f"https://wa.me/{clean_phone}" if clean_phone else "-"
                rating_str = f"{m.get('rating_gmaps', '0.0')} ({m.get('jumlah_review', '0')} ulasan)"

                w.writerow([
                    m.get("nama_bisnis", ""),
                    m.get("fokus_layanan", ""),
                    m.get("estimasi_kapasitas", ""),
                    rating_str,
                    phone or "-",
                    wa_link,
                    m.get("celah_kualitas", "-"),
                    m.get("celah_sop", "-"),
                    m.get("selling_point_rv", "-"),
                    m.get("website", "") or m.get("url_gmaps", "-"),
                    m.get("tanggal_update", ""),
                ])
        log.info(f"Matriks Kompetitor diekspor: {csv_file}")

    # 3. Market Signals to CSV
    sig_files = sorted(proc_dir.glob("market_signals_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if sig_files:
        with open(sig_files[0], "r", encoding="utf-8") as f:
            sigs = json.load(f)
        csv_file = proc_dir / "sinyal_pasar.csv"
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([
                "Sinyal / Tren Produk", "Platform", "Tingkat Demand",
                "Peluang untuk RUANG VISUAL", "Link Referensi", "Tanggal"
            ])
            for s in sigs:
                w.writerow([
                    s.get("signal", ""),
                    s.get("platform", "TikTok").title(),
                    s.get("metrik", ""),
                    s.get("relevansi", ""),
                    s.get("url", ""),
                    s.get("tanggal", ""),
                ])
        log.info(f"Sinyal Pasar diekspor: {csv_file}")


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
    log.info("Memulai eksekusi pipeline lengkap RUANG VISUAL...")

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
            from scrapers.utils import deduplicate_leads
            clean_leads, dup_count = deduplicate_leads(leads_only)
            log.info(f"Deduplikasi Leads: {len(clean_leads)} baru, {dup_count} duplikat disaring")

            if clean_leads:
                leads_count = len(clean_leads)
                hot_leads = [l for l in clean_leads if float(l.get("skor", 0)) >= 8.0]

                proc_path = PROCESSED_DIR / f"leads_scored_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
                with open(proc_path, "w", encoding="utf-8") as f:
                    json.dump(clean_leads, f, ensure_ascii=False, indent=2)

                if not dry_run:
                    export_leads_to_sheet(clean_leads)
                log.info(f"Leads selesai: {leads_count} baru ditemukan ({len(hot_leads)} hot leads)")
            else:
                log.info("Semua prospek yang ditemukan sudah ada di database riwayat.")
    except Exception as e:
        log.error(f"Error saat scraping leads: {e}")
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

    # 2. Facebook Marketplace Makassar (Leads, Competitor Benchmark & Trends)
    try:
        log.info("\n--- [2/5] Scraping Facebook Marketplace Makassar ---")
        from scrapers.facebook_marketplace_scraper import (
            scrape_marketplace_query, process_fb_leads, export_fb_leads_to_sheet,
            process_fb_competitors, export_fb_competitors_to_sheet,
            process_fb_trends, export_fb_signals_to_sheet
        )
        from patchright.sync_api import sync_playwright
        from scrapers.utils import launch_stealth_browser
        from scrapers.config import FB_LEAD_QUERIES, FB_COMPETITOR_QUERIES

        fb_leads_raw = []
        fb_comps_raw = []
        with sync_playwright() as p:
            browser = launch_stealth_browser(p, headless=True)
            page = browser.new_page()
            for q in FB_LEAD_QUERIES[:1]:
                fb_leads_raw.extend(scrape_marketplace_query(page, q, limit=10))
            for q in FB_COMPETITOR_QUERIES[:1]:
                fb_comps_raw.extend(scrape_marketplace_query(page, q, limit=10))
            browser.close()

        if fb_leads_raw:
            fb_leads = process_fb_leads(fb_leads_raw)
            leads_count += len(fb_leads)
            hot_leads.extend([l for l in fb_leads if float(l.get("skor", 0)) >= 8.0])
            if not dry_run:
                export_fb_leads_to_sheet(fb_leads)

        if fb_comps_raw:
            fb_comps = process_fb_competitors(fb_comps_raw)
            if not dry_run:
                export_fb_competitors_to_sheet(fb_comps)

        fb_trends = process_fb_trends(fb_leads_raw, fb_comps_raw)
        if fb_trends:
            signals_count += len(fb_trends)
            if not dry_run:
                export_fb_signals_to_sheet(fb_trends)
        log.info(f"Facebook Marketplace selesai: {len(fb_leads_raw)} leads, {len(fb_comps_raw)} kompetitor, {len(fb_trends)} tren")
    except Exception as e:
        log.warning(f"Facebook Marketplace dilewati (bukan blocking error): {e}")

    # 3. Threads Intelligence Scraper (Leads, Competitors & Trends)
    try:
        log.info("\n--- [3/6] Scraping Threads Intelligence Makassar ---")
        from scrapers.threads_scraper import (
            scrape_threads, process_leads as process_th_leads,
            export_leads_to_sheet as export_th_leads,
            export_competitors_to_sheet as export_th_comps,
            export_trends_to_sheet as export_th_trends
        )
        from scrapers.config import THREADS_LEAD_KEYWORDS, THREADS_COMPETITOR_KEYWORDS, THREADS_TREND_KEYWORDS

        th_limit = max(1, min(1, limit))
        th_leads_raw = scrape_threads(THREADS_LEAD_KEYWORDS, mode="leads", max_keywords=th_limit)
        if th_leads_raw:
            th_leads = process_th_leads(th_leads_raw)
            leads_count += len(th_leads)
            hot_leads.extend([l for l in th_leads if float(l.get("skor", 0)) >= 8.0])
            if not dry_run:
                export_th_leads(th_leads)

        th_comps_raw = scrape_threads(THREADS_COMPETITOR_KEYWORDS, mode="competitors", max_keywords=th_limit)
        if th_comps_raw and not dry_run:
            export_th_comps(th_comps_raw)

        th_trends_raw = scrape_threads(THREADS_TREND_KEYWORDS, mode="trends", max_keywords=th_limit)
        if th_trends_raw:
            signals_count += len(th_trends_raw)
            if not dry_run:
                export_th_trends(th_trends_raw)

        log.info(f"Threads selesai: {len(th_leads_raw)} leads, {len(th_comps_raw)} kompetitor, {len(th_trends_raw)} tren")
    except Exception as e:
        log.warning(f"Threads Intelligence dilewati (bukan blocking error): {e}")

    # 4. Food Delivery Makassar (GoFood Merchant Leads)
    try:
        log.info("\n--- [4/7] Scraping Merchant Kuliner Makassar (GoFood) ---")
        from scrapers.food_delivery_scraper import scrape_gofood_merchants, enrich_with_contact
        from scrapers.utils import deduplicate_leads
        food_raw = scrape_gofood_merchants(limit=limit)
        if food_raw:
            food_leads = enrich_with_contact(food_raw)
            clean_food, dup_food = deduplicate_leads(food_leads)
            log.info(f"Deduplikasi GoFood: {len(clean_food)} baru, {dup_food} duplikat disaring")
            if clean_food:
                leads_count += len(clean_food)
                hot_leads.extend([l for l in clean_food if float(l.get("skor", 0)) >= 8.0])
                if not dry_run:
                    export_leads_to_sheet(clean_food)
            log.info(f"GoFood selesai: {len(clean_food)} merchant kuliner baru ditambahkan")
    except Exception as e:
        log.warning(f"GoFood Merchant Scraper dilewati (bukan blocking error): {e}")

    # 5. Competitor Matrix
    try:
        log.info("\n--- [5/7] Menganalisis Matriks Kompetitor Makassar ---")
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
            log.info(f"Matriks kompetitor selesai: {competitor_count} percetakan teranalisis")
    except Exception as e:
        log.error(f"Error saat analisis kompetitor: {e}")
        try:
            send_error_alert("Competitor Matrix Analyzer", str(e))
        except Exception:
            pass

    # 6. Market Signals (TikTok Trends)
    try:
        log.info("\n--- [6/7] Memindai Tren Pasar (Market Signals) ---")
        signals = scan_market_signals(TIKTOK_KEYWORDS)
        signals_count = len(signals)
        sig_file = PROCESSED_DIR / f"market_signals_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
        with open(sig_file, "w", encoding="utf-8") as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        if not dry_run:
            export_signals_to_sheet(signals)
        log.info(f"Sinyal pasar selesai: {signals_count} tren terpetakan")
    except Exception as e:
        log.error(f"Error saat memindai tren pasar: {e}")
        try:
            send_error_alert("Market Signals Scraper", str(e))
        except Exception:
            pass

    # 7. Export CSV
    try:
        log.info("\n--- [7/7] Mengekspor Data ke CSV Lokal ---")
        run_export_csv()
    except Exception as e:
        log.warning(f"Gagal ekspor CSV: {e}")

    duration = time.time() - start_time
    log.info(f"\nSeluruh rangkaian pipeline selesai dalam {duration:.1f} detik.")

    # 5. Kirim Telegram Notification
    if notify_telegram:
        log.info("Mengirimkan laporan eksekutif ke Telegram...")
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
            log.warning(f"Gagal mengirim notifikasi Telegram: {e}")


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
    elif module in ("facebook", "fb"):
        print_banner()
        run_facebook()
    elif module in ("instagram", "ig"):
        print_banner()
        run_instagram()
    elif module in ("tiktok", "tt"):
        print_banner()
        run_tiktok()
    elif module in ("threads", "th"):
        print_banner()
        run_threads()
    elif module == "matrix":
        print_banner()
        run_matrix()
    elif module in ("clean-sheets", "bersihkan"):
        print_banner()
        run_clean_sheets()
    elif module in ("bot", "telegram"):
        print_banner()
        run_telegram_bot()
    elif module in ("export-csv", "csv"):
        print_banner()
        run_export_csv()
    elif module == "init-sheets":
        print_banner()
        run_init_sheets()
    elif module in ("enrich-web", "enrich"):
        print_banner()
        from scrapers.web_enricher import main as run_web_enricher
        run_web_enricher()
    elif module in ("dedup", "deduplicate"):
        print_banner()
        run_dedup()
    elif module in ("food", "gofood", "kuliner"):
        print_banner()
        run_food()
    elif module in ("help", "--help", "-h"):
        print_help()
    else:
        print(f"[ERROR] Module tidak dikenal: '{module}'")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
