"""
RUANG VISUAL — Threads Intelligence Scraper
============================================
Modul pemantauan Threads untuk 3 jalur intelijen bisnis:
1. Prospek: Post bisnis lokal Makassar yang aktif promosi & berpotensi butuh jasa cetak.
2. Kompetitor: Vendor percetakan lokal Makassar yang aktif berpromosi di Threads.
3. Market Signals: Tren branding, packaging, dan desain visual yang sedang viral.

Berjalan otomatis tanpa login.
Bebas dari semua karakter emoji dan emoticon.
"""

import re
import sys
import json
import time
import urllib.parse
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from patchright.sync_api import sync_playwright

from scrapers.config import (
    THREADS_LEAD_KEYWORDS,
    THREADS_COMPETITOR_KEYWORDS,
    THREADS_TREND_KEYWORDS,
    THREADS_DELAY_SECONDS,
    THREADS_MAX_PAGES_PER_SESSION,
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

log = get_logger("threads")

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
    "Sinyal / Tren Produk", "Platform", "Tingkat Demand",
    "Peluang untuk RUANG VISUAL", "Link Referensi", "Tanggal"
]


def build_threads_search_url(query: str) -> str:
    """Buat URL pencarian Threads."""
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.threads.net/search?q={encoded}&serp_type=default"


def extract_username_from_url(url: str) -> str:
    """Ekstrak username dari URL Threads."""
    match = re.search(r'threads\.net/@([^/\?]+)', url)
    return match.group(1) if match else ""


def extract_phone_from_text(text: str) -> str:
    """Ekstrak nomor telepon dari teks."""
    if not text:
        return ""
    
    patterns = [
        r'(?:62|0)8\d{8,11}',
        r'(?:WA|wa|WhatsApp|whatsapp)[:\s]*(?:62|0)8\d{8,11}',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return ""


def scrape_threads_search(keyword: str, mode: str, page_context, max_posts: int = 10) -> list[dict]:
    """
    Scrape hasil pencarian Threads untuk keyword tertentu.
    
    Args:
        keyword: Kata kunci pencarian
        mode: Mode scraping (leads, competitors, trends)
        page_context: Browser page context
        max_posts: Maksimal post yang diambil per keyword
    
    Returns:
        List of dict dengan data post Threads
    """
    url = build_threads_search_url(keyword)
    log.info(f"Scraping keyword: '{keyword}' (mode: {mode})")
    
    try:
        page = page_context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
        
        results = []
        scroll_attempts = 0
        max_scrolls = 5
        
        while len(results) < max_posts and scroll_attempts < max_scrolls:
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            time.sleep(2)
            scroll_attempts += 1
            
            # Ekstrak data post dari halaman
            posts = page.query_selector_all('div[role="button"]')
            
            for post in posts[:max_posts]:
                try:
                    text_content = post.inner_text() if post else ""
                    
                    # Ekstrak username/nama akun
                    username_elem = post.query_selector('a[href*="/@"]')
                    profile_url = username_elem.get_attribute("href") if username_elem else ""
                    username = extract_username_from_url(profile_url) if profile_url else ""
                    
                    # Ekstrak engagement metrics (likes, replies)
                    engagement_text = ""
                    engagement_elems = post.query_selector_all('span')
                    for elem in engagement_elems:
                        txt = elem.inner_text()
                        if re.search(r'\d+', txt):
                            engagement_text += txt + " "
                    
                    # Ekstrak nomor telepon dari konten
                    phone = extract_phone_from_text(text_content)
                    
                    # Skip jika data tidak lengkap
                    if not username or not text_content:
                        continue
                    
                    data = {
                        "nama_bisnis": username,
                        "username": username,
                        "profile_url": f"https://www.threads.net/@{username}" if username else "",
                        "post_text": text_content[:500],
                        "engagement": engagement_text.strip(),
                        "no_telepon": phone,
                        "keyword": keyword,
                        "scrape_date": today_wita(),
                        "mode": mode,
                    }
                    
                    results.append(data)
                    
                    if len(results) >= max_posts:
                        break
                        
                except Exception as e:
                    log.debug(f"Error parsing post: {e}")
                    continue
        
        page.close()
        rate_limit(THREADS_DELAY_SECONDS)
        
        log.info(f"Berhasil scrape {len(results)} posts untuk keyword '{keyword}'")
        return results
        
    except Exception as e:
        log.error(f"Error scraping keyword '{keyword}': {e}")
        return []


def scrape_threads(keywords: list[str], mode: str, max_keywords: int = None) -> list[dict]:
    """
    Scrape Threads untuk multiple keywords.
    
    Args:
        keywords: List keyword untuk di-scrape
        mode: Mode scraping (leads, competitors, trends)
        max_keywords: Limit jumlah keywords yang diproses
    
    Returns:
        List of dict dengan data hasil scraping
    """
    if max_keywords:
        keywords = keywords[:max_keywords]
    
    log.info(f"Memulai Threads scraping - Mode: {mode} | Keywords: {len(keywords)}")
    
    all_results = []
    
    with sync_playwright() as p:
        browser = launch_stealth_browser(p)
        browser_context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        try:
            for keyword in keywords:
                results = scrape_threads_search(keyword, mode, browser_context, max_posts=10)
                all_results.extend(results)
                
        finally:
            browser.close()
    
    # Deduplikasi berdasarkan username
    seen_usernames = set()
    unique_results = []
    for item in all_results:
        username = item.get("username", "")
        if username and username not in seen_usernames:
            seen_usernames.add(username)
            unique_results.append(item)
    
    log.info(f"Total data unik terkumpul: {len(unique_results)}")
    return unique_results


def process_leads(raw_data: list[dict]) -> list[dict]:
    """Process & score leads dari Threads."""
    processed = []
    
    for item in raw_data:
        kategori_kode = detect_category(
            nama_bisnis=item.get("nama_bisnis", ""),
            alamat="",
            kategori_gmaps=""
        )
        
        pemicu = f"Postingan Threads aktif keyword '{item.get('keyword', '')}' - mencari vendor cetak"
        rekomendasi = "Banner roll-up & kartu nama finishing doff" if "bisnis" in item.get("keyword", "") else "Stiker kemasan waterproof & box packaging custom"
        
        scored = score_and_format(
            nama_bisnis=item.get("nama_bisnis", ""),
            kategori_kode=kategori_kode,
            rating=0,
            jumlah_review=0,
            no_telepon=item.get("no_telepon", ""),
            website=item.get("profile_url", ""),
            instagram="",
            alamat="Makassar",
            gmaps_url="",
        )

        scored["threads_url"] = item.get("profile_url", "")
        scored["post_preview"] = item.get("post_text", "")[:200]
        scored["engagement"] = item.get("engagement", "")
        scored["scrape_date"] = item.get("scrape_date", today_wita())
        scored["platform_sumber"] = "Threads"
        scored["url_sumber"] = item.get("profile_url", "")
        scored["pemicu_kebutuhan"] = pemicu
        scored["rekomendasi_produk"] = rekomendasi
        
        processed.append(scored)
    
    return processed


def export_leads_to_sheet(leads: list[dict]):
    """Export leads ke Google Sheets tab 'Radar Prospek'."""
    if not leads:
        log.info("Tidak ada leads untuk di-export")
        return
    from scrapers.gmaps_scraper import export_leads_to_sheet as gmaps_export
    gmaps_export(leads, action="append")


def export_competitors_to_sheet(competitors: list[dict]):
    """Export competitors ke Google Sheets tab 'Matriks Kompetitor'."""
    if not competitors:
        log.info("Tidak ada kompetitor untuk di-export")
        return
    
    rows = []
    for comp in competitors:
        threads_link = f'=HYPERLINK("{comp.get("profile_url", "")}", "Threads")' if comp.get("profile_url") else "-"
        wa_link = f'=HYPERLINK("https://wa.me/{comp.get("no_telepon", "").replace("0", "62", 1)}", "Chat WA")' if comp.get("no_telepon") else "-"
        
        row = [
            comp.get("nama_bisnis", ""),
            "Digital printing & percetakan",
            "Monitoring diperlukan via Module F",
            f"Engagement: {comp.get('engagement', '-')}",
            comp.get("no_telepon", "-"),
            wa_link,
            "Analisis konten visual diperlukan",
            "Analisis responsiveness diperlukan",
            "Kualitas premium & SOP ketat RUANG VISUAL",
            threads_link,
            today_wita(),
        ]
        rows.append(row)
    
    try:
        append_rows_to_sheet("Matriks Kompetitor", rows, action="append", headers=HEADERS_MATRIKS_KOMPETITOR)
        log.info(f"{len(rows)} kompetitor berhasil di-export ke 'Matriks Kompetitor'")
    except Exception as e:
        log.warning(f"Belum bisa export ke Google Sheets: {e}")


def export_trends_to_sheet(trends: list[dict]):
    """Export market signals ke Google Sheets tab 'Market Signals'."""
    if not trends:
        log.info("Tidak ada trends untuk di-export")
        return
    
    rows = []
    for trend in trends:
        keyword = trend.get("keyword", "")
        username = trend.get("username", "")
        signal = f"Tren Threads: {keyword}"
        tingkat_demand = f"Engagement {trend.get('engagement', 'Aktif')}"
        post_snippet = trend.get('post_text', '').replace('\n', ' ')[:120]
        peluang = f"Post dari @{username}: {post_snippet}... Potensi kebutuhan desain dan cetak kemasan."
        link_ref = trend.get("url") or build_threads_search_url(keyword)
        
        row = [
            signal,
            "Threads",
            tingkat_demand,
            peluang,
            link_ref,
            today_wita(),
        ]
        rows.append(row)
    
    try:
        append_rows_to_sheet("Market Signals", rows, action="append", headers=HEADERS_MARKET_SIGNALS)
        log.info(f"{len(rows)} trends berhasil di-export ke 'Market Signals'")
    except Exception as e:
        log.warning(f"Belum bisa export ke Google Sheets: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="RUANG VISUAL - Threads Intelligence Scraper"
    )
    parser.add_argument(
        "--mode",
        choices=["leads", "competitors", "trends", "all"],
        default="leads",
        help="Mode scraping: leads, competitors, trends, atau all",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit jumlah keywords yang diproses (default: semua)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya scrape dan simpan JSON, tidak export ke Google Sheets",
    )
    args = parser.parse_args()
    
    log.info("=" * 60)
    log.info("RUANG VISUAL - Threads Intelligence Scraper")
    log.info(f"   Mode: {args.mode} | Limit: {args.limit or 'semua'}")
    log.info("=" * 60)
    
    if args.mode in ("leads", "all"):
        log.info("\nSCRAPING LEADS...")
        raw_leads = scrape_threads(THREADS_LEAD_KEYWORDS, mode="leads", max_keywords=args.limit)
        
        if raw_leads:
            raw_path = RAW_DIR / f"threads_leads_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_leads, f, ensure_ascii=False, indent=2)
            log.info(f"Raw data disimpan: {raw_path}")
            
            processed = process_leads(raw_leads)
            
            proc_path = PROCESSED_DIR / f"threads_leads_scored_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(proc_path, "w", encoding="utf-8") as f:
                json.dump(processed, f, ensure_ascii=False, indent=2)
            log.info(f"Processed data disimpan: {proc_path}")
            
            if not args.dry_run:
                export_leads_to_sheet(processed)
            else:
                log.info(f"[DRY RUN] {len(processed)} leads siap di-export:")
                for l in processed[:5]:
                    log.info(f"  -> {l['nama_bisnis']} | Skor: {l['skor']}/10 ({l['skor_label']})")
    
    if args.mode in ("competitors", "all"):
        log.info("\nSCRAPING COMPETITORS...")
        raw_competitors = scrape_threads(THREADS_COMPETITOR_KEYWORDS, mode="competitors", max_keywords=args.limit)
        
        if raw_competitors:
            raw_path = RAW_DIR / f"threads_competitors_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_competitors, f, ensure_ascii=False, indent=2)
            log.info(f"Raw data disimpan: {raw_path}")
            
            if not args.dry_run:
                export_competitors_to_sheet(raw_competitors)
            else:
                log.info(f"[DRY RUN] {len(raw_competitors)} kompetitor siap di-export:")
                for c in raw_competitors[:5]:
                    log.info(f"  -> {c.get('nama_bisnis')} | @{c.get('username')}")
    
    if args.mode in ("trends", "all"):
        log.info("\nSCRAPING TRENDS (Market Signals)...")
        raw_trends = scrape_threads(THREADS_TREND_KEYWORDS, mode="trends", max_keywords=args.limit)
        
        if raw_trends:
            raw_path = RAW_DIR / f"threads_trends_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_trends, f, ensure_ascii=False, indent=2)
            log.info(f"Raw data disimpan: {raw_path}")
            
            if not args.dry_run:
                export_trends_to_sheet(raw_trends)
            else:
                log.info(f"[DRY RUN] {len(raw_trends)} trends siap di-export:")
                for t in raw_trends[:5]:
                    log.info(f"  -> {t.get('keyword')} | @{t.get('username')} | {t.get('engagement')}")
    
    log.info("\nSelesai.")


if __name__ == "__main__":
    main()
