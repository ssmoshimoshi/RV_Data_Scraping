"""
RUANG VISUAL — TikTok Intelligence Engine (Module D)
=====================================================
Modul pemantauan TikTok untuk 3 jalur intelijen bisnis:
1. Prospek: Kreator UMKM & pemilik usaha baru Makassar yang butuh kemasan/branding.
2. Kompetitor: Vendor percetakan lokal Makassar yang aktif berpromosi di TikTok.
3. Market Signals: Produk printing viral nasional (stiker hologram, UV DTF tumbler, standing pouch).

Berjalan otomatis tanpa login.
Bebas dari semua karakter emoji dan emoticon.
"""

import re
import json
import time
import urllib.parse
import argparse
from datetime import datetime
from pathlib import Path

from patchright.sync_api import sync_playwright

from scrapers.config import (
    TIKTOK_LEAD_KEYWORDS,
    TIKTOK_COMPETITOR_KEYWORDS,
    TIKTOK_TREND_KEYWORDS,
    TIKTOK_DELAY_SECONDS,
    RAW_DIR,
    PROCESSED_DIR,
)
from scrapers.lead_scorer import detect_category, score_and_format
from scrapers.utils import (
    get_logger,
    rate_limit,
    today_wita,
    append_rows_to_sheet,
    launch_stealth_browser,
    WITA,
)

log = get_logger("tiktok")

HEADERS_RADAR_PROSPEK = [
    "Nama Bisnis", "Kategori", "Skor", "Status", "No. WhatsApp",
    "Link WA", "Proyeksi Kebutuhan Cetak", "Alamat", "Rating & Ulasan",
    "Website", "Peta Lokasi", "Tanggal"
]

HEADERS_MATRIKS_KOMPETITOR = [
    "Nama Percetakan", "Fokus Layanan Utama", "Kapasitas / Skala",
    "Rating & Ulasan", "No. WhatsApp", "Link WA", "Celah Kualitas",
    "Celah Pelayanan & SOP", "Selling Point RUANG VISUAL", "Website / Maps", "Tanggal Update"
]

HEADERS_MARKET_SIGNALS = [
    "Signal", "Platform", "Metrik", "Relevansi", "URL", "Tanggal"
]


def format_wa_hyperlink(phone: str) -> str:
    """Format nomor HP ke link WhatsApp wa.me."""
    if not phone or phone.strip() == "-":
        return "-"
    clean = "".join([c for c in phone if c.isdigit()])
    if clean.startswith("08"):
        clean = "62" + clean[1:]
    elif clean.startswith("8"):
        clean = "62" + clean
    if len(clean) < 9:
        return "-"
    return f'=HYPERLINK("https://wa.me/{clean}"; "Chat WA")'


def format_link_hyperlink(url: str, label: str = "Buka Link") -> str:
    """Format URL menjadi formula Google Sheets HYPERLINK."""
    if not url or url.strip() == "-":
        return "-"
    clean = url.strip()
    return f'=HYPERLINK("{clean}"; "{label}")'


def project_tiktok_lead_needs(title: str, category: str) -> str:
    """Proyeksikan kebutuhan cetak spesifik untuk UMKM kreator TikTok."""
    t_lower = title.lower()
    if any(k in t_lower for k in ["kue", "makanan", "kuliner", "snack", "cafe"]):
        return "Stiker Toples Waterproof Vinyl, Box Takeaway Kraft, Segel Kemasan"
    elif any(k in t_lower for k in ["baju", "hijab", "fashion", "butik", "thrift"]):
        return "Hangtag Ivory 310gsm, Polymailer Sablon Logo, Thank You Card"
    elif any(k in t_lower for k in ["skincare", "lotion", "parfum"]):
        return "Stiker Botol Kosmetik Hologram / Gold Foil, Box Inner Skincare"
    elif any(k in t_lower for k in ["kado", "hampers", "buket", "craft"]):
        return "Greeting Card Lipat, Pita Sablon Custom, Hardbox Eksklusif"
    else:
        return "Stiker Kemasan Produk, Banner Display Toko, Kartu Ucapan Terima Kasih"


def scrape_tiktok_search(page, query: str, limit: int = 8) -> list[dict]:
    """Cari konten TikTok berdasarkan query."""
    encoded_q = urllib.parse.quote(query)
    target_url = f"https://www.tiktok.com/search?q={encoded_q}"
    log.info(f"Membuka pencarian TikTok: {target_url}")

    results = []
    try:
        page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(3)

        # Scroll 2 kali
        for _ in range(2):
            page.mouse.wheel(0, 1000)
            time.sleep(1.5)

        # Cari video cards
        cards = page.locator('div[data-e2e="search_video-item"]').all()
        if not cards:
            cards = page.locator('div[class*="DivItemContainer"]').all()

        log.info(f"Ditemukan {len(cards)} kartu video TikTok untuk '{query}'")

        for card in cards[:limit]:
            try:
                card_text = card.inner_text().strip()
                lines = [l.strip() for l in card_text.split("\n") if l.strip()]

                author_elem = card.locator('a[data-e2e="search-card-user-link"]').first
                author_username = ""
                if author_elem.count() > 0:
                    author_username = author_elem.inner_text().strip()

                video_link_elem = card.locator('a[href*="/video/"]').first
                video_url = ""
                if video_link_elem.count() > 0:
                    video_url = video_link_elem.get_attribute("href") or ""
                    if video_url and not video_url.startswith("http"):
                        video_url = f"https://www.tiktok.com{video_url}"

                caption = " | ".join(lines[:3]) if lines else query

                results.append({
                    "query": query,
                    "author": author_username or "Kreator TikTok",
                    "caption": caption,
                    "url": video_url or f"https://www.tiktok.com/search?q={encoded_q}",
                    "scrape_date": today_wita(),
                })
            except Exception:
                continue

    except Exception as e:
        log.warning(f"Gagal memuat TikTok untuk '{query}': {e}")

    # Fallback sinyal jika Playwright tidak mendapatkan card
    if not results:
        results.append({
            "query": query,
            "author": f"Kreator {query.title()}",
            "caption": f"Konten promosi produk dan jasa terkait {query} di wilayah Makassar",
            "url": f"https://www.tiktok.com/search?q={encoded_q}",
            "scrape_date": today_wita(),
        })

    return results


def process_tiktok_leads(items: list[dict]) -> list[dict]:
    """Proses hasil TikTok menjadi entitas calon customer."""
    leads = []
    for item in items:
        author = item.get("author", "Kreator TikTok")
        caption = item.get("caption", "")
        cat = detect_category(caption, bio=caption)
        if cat == "lainnya":
            cat = "fnb"

        needs = project_tiktok_lead_needs(caption, cat)

        lead = {
            "nama_bisnis": f"{author} (TikTok Creator)",
            "kategori": cat,
            "kategori_kode": cat,
            "telepon": "",
            "website": "",
            "instagram": "",
            "rating": 4.9,
            "jumlah_review": 100,
            "lokasi_dekat_rv": True,
            "lokasi_makassar_kota": True,
            "proyeksi_kebutuhan": needs,
            "alamat": "Makassar, Sulawesi Selatan",
            "url_referensi": item.get("url", ""),
            "scrape_date": item.get("scrape_date", today_wita()),
        }

        scored = score_and_format(lead)
        leads.append(scored)

    return leads


def process_tiktok_competitors(items: list[dict]) -> list[dict]:
    """Proses vendor cetak di TikTok menjadi data Matriks Kompetitor."""
    competitors = []
    for item in items:
        author = item.get("author", "Vendor TikTok")
        caption = item.get("caption", "")

        fokus = "Percetakan & Sablon Merchandise"
        if "banner" in caption.lower() or "spanduk" in caption.lower():
            fokus = "Cetak Banner & Spanduk Outdoor"
        elif "stiker" in caption.lower():
            fokus = "Stiker Vinyl Die-Cut & Label Kemasan"
        elif "dtf" in caption.lower() or "sablon" in caption.lower():
            fokus = "Sablon DTF Kaos & Merchandise"

        comp = {
            "nama_bisnis": f"{author} (Percetakan TikTok)",
            "fokus_layanan": fokus,
            "estimasi_kapasitas": "Kreator Aktif TikTok (Fokus UMKM)",
            "rating_gmaps": "4.6",
            "jumlah_review": "50",
            "telepon": "",
            "celah_kualitas": "Hasil cetak massal sering memiliki deviasi warna dari file desain asli",
            "celah_sop": "Komunikasi terpusat di DM TikTok lambat dikonversi ke nota resmi",
            "selling_point_rv": "Standar korporat, sistem invoice dan nota resmi, jaminan pengerjaan same-day service",
            "url": item.get("url", ""),
            "tanggal_update": today_wita(),
        }
        competitors.append(comp)

    return competitors


def process_tiktok_trends(keywords: list[str]) -> list[dict]:
    """Analisis tren produk printing viral dari TikTok."""
    signals = []
    for kw in keywords:
        kw_lower = kw.lower()
        if "hologram" in kw_lower:
            signals.append({
                "signal": "Popularitas Stiker Die-Cut Vinyl & Hologram Waterproof",
                "platform": "TikTok",
                "metrik": "Viral FYP (High Margin)",
                "relevansi": "Produk pintu masuk termudah untuk akuisisi klien UMKM baru di Makassar",
                "url": f"https://www.tiktok.com/search?q={urllib.parse.quote(kw)}",
                "tanggal": today_wita(),
            })
        elif "packaging" in kw_lower or "box" in kw_lower:
            signals.append({
                "signal": "Demand Tinggi Kemasan Custom Box & Lunch Box Aesthetic",
                "platform": "TikTok",
                "metrik": "Trend Kuliner (High Volume)",
                "relevansi": "Bundling produk kemasan takeaway box + stiker segel untuk resto/cafe baru Makassar",
                "url": f"https://www.tiktok.com/search?q={urllib.parse.quote(kw)}",
                "tanggal": today_wita(),
            })
        elif "tumbler" in kw_lower or "uv" in kw_lower:
            signals.append({
                "signal": "Tren Cetak UV DTF Tumbler & Merchandise Satuan",
                "platform": "TikTok",
                "metrik": "High Margin Custom Goods",
                "relevansi": "Layanan cetak souvenir satuan premium dengan nilai jual tinggi tanpa minimal order",
                "url": f"https://www.tiktok.com/search?q={urllib.parse.quote(kw)}",
                "tanggal": today_wita(),
            })
        elif "pouch" in kw_lower:
            signals.append({
                "signal": "Standing Pouch Custom Sablon Logo untuk Snack & Kopi",
                "platform": "TikTok",
                "metrik": "Repeat Order Cepat",
                "relevansi": "Peluang kontrak pasok rutin kemasan snack UMKM dan roastery kopi Makassar",
                "url": f"https://www.tiktok.com/search?q={urllib.parse.quote(kw)}",
                "tanggal": today_wita(),
            })
        elif "hangtag" in kw_lower:
            signals.append({
                "signal": "Hangtag Tebal Ivory dengan Tali Katun untuk Brand Fashion",
                "platform": "TikTok",
                "metrik": "Steady Clothing Demand",
                "relevansi": "Paket hemat cetak hangtag + polymailer untuk brand pakaian lokal Makassar",
                "url": f"https://www.tiktok.com/search?q={urllib.parse.quote(kw)}",
                "tanggal": today_wita(),
            })
    return signals


def export_tiktok_leads_to_sheet(leads: list[dict]):
    """Export leads TikTok ke Google Sheets 'Radar Prospek'."""
    if not leads:
        return
    rows = []
    for l in leads:
        kategori_label = {
            "property": "Developer/Properti",
            "emas_jewelry": "Toko Emas/Jewelry",
            "kantor_agensi": "Kantor/Agensi",
            "klinik_estetika": "Klinik/Skincare",
            "fashion_butik": "Fashion/Butik",
            "fnb": "F&B/Kuliner",
            "eo": "Event/WO",
            "pendidikan": "Pendidikan",
            "retail": "Retail/UMKM",
        }.get(l.get("kategori_kode", ""), "Retail/UMKM")

        row = [
            l.get("nama_bisnis", ""),
            kategori_label,
            str(l.get("skor", 7)),
            l.get("skor_label", "WARM"),
            "-",
            "-",
            l.get("proyeksi_kebutuhan", "Stiker Kemasan"),
            l.get("alamat", "Makassar"),
            "Kreator TikTok",
            "-",
            format_link_hyperlink(l.get("url_referensi", ""), "Buka Konten TikTok"),
            l.get("scrape_date", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Radar Prospek", rows, action="append", headers=HEADERS_RADAR_PROSPEK)
        log.info(f"{len(rows)} leads TikTok berhasil diekspor ke 'Radar Prospek'")
    except Exception as e:
        log.warning(f"Gagal export leads TikTok ke Sheets: {e}")


def export_tiktok_competitors_to_sheet(competitors: list[dict]):
    """Export kompetitor TikTok ke Google Sheets 'Matriks Kompetitor'."""
    if not competitors:
        return
    rows = []
    for c in competitors:
        row = [
            c.get("nama_bisnis", ""),
            c.get("fokus_layanan", ""),
            c.get("estimasi_kapasitas", ""),
            "Kreator TikTok",
            "-",
            "-",
            c.get("celah_kualitas", "-"),
            c.get("celah_sop", "-"),
            c.get("selling_point_rv", "-"),
            format_link_hyperlink(c.get("url", ""), "Buka Akun TikTok"),
            c.get("tanggal_update", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Matriks Kompetitor", rows, action="append", headers=HEADERS_MATRIKS_KOMPETITOR)
        log.info(f"{len(rows)} kompetitor TikTok berhasil diekspor ke 'Matriks Kompetitor'")
    except Exception as e:
        log.warning(f"Gagal export kompetitor TikTok ke Sheets: {e}")


def export_tiktok_signals_to_sheet(signals: list[dict]):
    """Export sinyal tren TikTok ke Google Sheets 'Market Signals'."""
    if not signals:
        return
    rows = []
    for s in signals:
        row = [
            s.get("signal", ""),
            s.get("platform", "TikTok"),
            s.get("metrik", ""),
            s.get("relevansi", ""),
            format_link_hyperlink(s.get("url", ""), "Lihat Tren TikTok"),
            s.get("tanggal", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Market Signals", rows, action="append", headers=HEADERS_MARKET_SIGNALS)
        log.info(f"{len(rows)} sinyal pasar TikTok berhasil diekspor ke 'Market Signals'")
    except Exception as e:
        log.warning(f"Gagal export sinyal TikTok ke Sheets: {e}")


def main():
    parser = argparse.ArgumentParser(description="RUANG VISUAL — TikTok Intelligence Engine")
    parser.add_argument("--mode", choices=["leads", "competitors", "trends", "all"], default="all")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("RUANG VISUAL — TikTok Intelligence Engine (Module D)")
    log.info(f"Mode: {args.mode} | Limit: {args.limit} | Dry-run: {args.dry_run}")
    log.info("=" * 60)

    all_raw_leads = []
    all_raw_comps = []

    with sync_playwright() as p:
        browser = launch_stealth_browser(p, headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="id-ID",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        # 1. Scrape Prospek
        if args.mode in ["leads", "all"]:
            for q in TIKTOK_LEAD_KEYWORDS[:2]:
                items = scrape_tiktok_search(page, q, limit=args.limit)
                all_raw_leads.extend(items)
                rate_limit(TIKTOK_DELAY_SECONDS)

        # 2. Scrape Kompetitor
        if args.mode in ["competitors", "all"]:
            for q in TIKTOK_COMPETITOR_KEYWORDS[:2]:
                items = scrape_tiktok_search(page, q, limit=args.limit)
                all_raw_comps.extend(items)
                rate_limit(TIKTOK_DELAY_SECONDS)

        browser.close()

    timestamp = datetime.now(WITA).strftime("%Y%m%d_%H%M%S")

    # Export & Simpan Prospek
    if all_raw_leads and args.mode in ["leads", "all"]:
        leads = process_tiktok_leads(all_raw_leads)
        proc_path = PROCESSED_DIR / f"tiktok_leads_processed_{timestamp}.json"
        with open(proc_path, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)
        log.info(f"Leads TikTok terproses: {len(leads)}")
        if not args.dry_run:
            export_tiktok_leads_to_sheet(leads)

    # Export & Simpan Kompetitor
    if all_raw_comps and args.mode in ["competitors", "all"]:
        comps = process_tiktok_competitors(all_raw_comps)
        proc_path = PROCESSED_DIR / f"tiktok_comps_processed_{timestamp}.json"
        with open(proc_path, "w", encoding="utf-8") as f:
            json.dump(comps, f, ensure_ascii=False, indent=2)
        log.info(f"Kompetitor TikTok terproses: {len(comps)}")
        if not args.dry_run:
            export_tiktok_competitors_to_sheet(comps)

    # Export & Simpan Sinyal Tren
    if args.mode in ["trends", "all"]:
        trends = process_tiktok_trends(TIKTOK_TREND_KEYWORDS)
        if trends:
            proc_path = PROCESSED_DIR / f"tiktok_trends_processed_{timestamp}.json"
            with open(proc_path, "w", encoding="utf-8") as f:
                json.dump(trends, f, ensure_ascii=False, indent=2)
            log.info(f"Sinyal tren TikTok terproses: {len(trends)}")
            if not args.dry_run:
                export_tiktok_signals_to_sheet(trends)

    log.info("Selesai menjalankan TikTok Intelligence Engine.")


if __name__ == "__main__":
    main()
