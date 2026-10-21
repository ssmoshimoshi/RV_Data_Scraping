"""
RUANG VISUAL — Google Maps Scraper (Module B)
===============================================
Scrape data bisnis dari Google Maps untuk lead generation & competitor mapping.
Referensi: intelligence_pipeline_prd.md §7

Fitur:
    - Headless browser stealth via Patchright (menggunakan installed Google Chrome)
    - Scroll feed interaktif untuk mengambil batch listings
    - Ekstraksi Rating, Review Count, Kategori, Alamat, dan Link GMaps
    - Scoring otomatis via Lead Scoring Engine (Module E)
    - Franchise filter (blokir waralaba nasional 100%)
    - Export ke Google Sheets atau simpan lokal di data/raw/ & data/processed/
    - Rate limiting & deduplikasi otomatis
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import json
import time
import argparse
import urllib.parse
from datetime import datetime

from patchright.sync_api import sync_playwright

from scrapers.config import (
    GMAPS_LEAD_QUERIES,
    GMAPS_COMPETITOR_QUERIES,
    GMAPS_TREND_QUERIES,
    GMAPS_DELAY_SECONDS,
    RAW_DIR,
    PROCESSED_DIR,
    RV_LATITUDE,
    RV_LONGITUDE,
)
from scrapers.lead_scorer import detect_category, score_and_format, is_near_rv
from scrapers.franchise_filter import is_national_franchise, filter_franchise_from_leads
from scrapers.utils import (
    get_logger,
    rate_limit,
    today_wita,
    now_wita,
    save_raw_json,
    append_rows_to_sheet,
    get_existing_names,
    log_scrape_run,
    launch_stealth_browser,
    WITA,
)

log = get_logger("gmaps")


# ─── URL Builder ─────────────────────────────────────────────────────────────
def build_gmaps_search_url(query: str) -> str:
    """Buat URL pencarian Google Maps berpusat pada koordinat workshop RUANG VISUAL."""
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.google.com/maps/search/{encoded}/@{RV_LATITUDE},{RV_LONGITUDE},15z"


# ─── Browser-Based Scraper ───────────────────────────────────────────────────
def scrape_gmaps_query_browser(query: str, max_scrolls: int = 2) -> list[dict]:
    """
    Scrape 1 search query dari Google Maps menggunakan headless browser stealth.
    Menggunakan Patchright / Playwright (Chrome di macOS, Chromium di Linux CI).
    """
    url = build_gmaps_search_url(query)
    results = []

    with sync_playwright() as p:
        browser = launch_stealth_browser(p, headless=True)
        context = browser.new_context(
            locale="id-ID",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_selector('a[href*="/maps/place/"], div.Nv2PK', timeout=12000)
        except Exception as e:
            log.warning(f"  Timeout atau selektor tidak ditemukan untuk '{query}': {e}")
            browser.close()
            return []

        # Scroll feed untuk memuat lebih banyak listing
        feed = page.query_selector('div[role="feed"]')
        if feed:
            for _ in range(max_scrolls):
                feed.evaluate("el => el.scrollBy(0, 1000)")
                page.wait_for_timeout(800)

        cards = page.query_selector_all("div.Nv2PK")
        seen_names = set()

        for card in cards:
            try:
                link = card.query_selector('a[href*="/maps/place/"]')
                if not link:
                    continue

                name = link.get_attribute("aria-label")
                if not name or name in seen_names:
                    continue
                seen_names.add(name)

                href = link.get_attribute("href") or ""

                # Rating & Review Count
                rating = 0.0
                reviews = 0
                star_el = card.query_selector("span.MW4etd")
                if star_el:
                    try:
                        rating = float(star_el.inner_text().strip().replace(",", "."))
                    except Exception:
                        pass

                review_el = card.query_selector("span.UY7F9")
                if review_el:
                    m = re.search(r"([\d,.]+)", review_el.inner_text())
                    if m:
                        reviews = int(m.group(1).replace(",", "").replace(".", ""))

                # Kategori, Alamat, dan Telepon
                category = ""
                address = ""
                phone = ""
                text_lines = [t.strip() for t in card.inner_text().split("\n") if t.strip()]

                for line in text_lines:
                    # Deteksi nomor telepon Indonesia
                    if not phone:
                        pm = re.search(r'((?:\+62|08)[0-9]{1,4}[- ]?[0-9]{3,5}[- ]?[0-9]{3,5}|\(0411\)[- ]?[0-9]{5,7})', line)
                        if pm:
                            phone = pm.group(1).strip()

                    if " · " in line:
                        # Abaikan baris status operasional
                        if any(w in line.lower() for w in ["tutup", "buka", "closed", "open", "order", "pesan"]):
                            continue
                        parts = [p.strip() for p in line.split(" · ") if p.strip()]
                        if len(parts) >= 1 and not category:
                            category = parts[0]
                        if len(parts) >= 2 and not address:
                            cleaned_addr = re.sub(r'[^\x20-\x7E\s]', '', parts[1]).strip()
                            if cleaned_addr and len(cleaned_addr) > 2:
                                address = cleaned_addr

                # Website link
                website = ""
                web_el = card.query_selector('a[aria-label*="Website"], a[data-value="Website"], a:has-text("Website")')
                if web_el:
                    raw_href = web_el.get_attribute("href") or ""
                    if raw_href.startswith("http"):
                        website = raw_href
                    elif "adurl=" in raw_href:
                        m_url = re.search(r'adurl=([^&]+)', raw_href)
                        if m_url:
                            website = urllib.parse.unquote(m_url.group(1))

                results.append({
                    "nama_bisnis": name.strip(),
                    "url_gmaps": href,
                    "kategori": category,
                    "alamat": address,
                    "telepon": phone,
                    "website": website,
                    "rating": rating,
                    "jumlah_review": reviews,
                    "scrape_date": today_wita(),
                    "source": "google_maps",
                    "query_used": query,
                })
            except Exception as e:
                log.debug(f"Error parsing card: {e}")
                continue

        browser.close()

    return results


# ─── Main Scraping Orchestrator ──────────────────────────────────────────────
def scrape_gmaps(queries: list[str], max_queries: int = None, mode: str = "leads") -> list[dict]:
    """
    Scrape Google Maps untuk daftar queries.
    """
    all_results = []
    queries_to_run = queries[:max_queries] if max_queries else queries

    log.info(f"Memulai Google Maps scraping ({mode}) - {len(queries_to_run)} queries")

    # Ambil nama yang sudah ada di sheet untuk deduplikasi
    sheet_name = "Radar Prospek" if mode == "leads" else "Matriks Kompetitor"
    try:
        existing = get_existing_names(sheet_name)
        log.info(f"{len(existing)} entri sudah ada di '{sheet_name}'")
    except Exception as e:
        log.info(f"Sheet '{sheet_name}' belum terbaca (akan disimpan lokal): {e}")
        existing = set()

    for i, query in enumerate(queries_to_run, 1):
        start_time = time.time()
        log.info(f"[{i}/{len(queries_to_run)}] Searching: '{query}'")

        try:
            results = scrape_gmaps_query_browser(query, max_scrolls=2)

            # Deduplikasi
            new_results = []
            for r in results:
                name_lower = r["nama_bisnis"].strip().lower()
                if name_lower not in existing and name_lower not in {
                    x["nama_bisnis"].strip().lower() for x in all_results
                }:
                    new_results.append(r)
                    existing.add(name_lower)

            duration = int(time.time() - start_time)
            log.info(f"  Found: {len(results)} total, {len(new_results)} new ({duration}s)")
            all_results.extend(new_results)

            # Log ke sheet jika memungkinkan
            try:
                log_scrape_run(
                    module=f"Module B ({mode})",
                    platform="google_maps",
                    query=query,
                    results_count=len(new_results),
                    status="SUCCESS",
                    duration_sec=duration,
                )
            except Exception:
                pass

        except Exception as e:
            log.error(f"  [ERROR] Error scraping '{query}': {e}")
            try:
                log_scrape_run(
                    module=f"Module B ({mode})",
                    platform="google_maps",
                    query=query,
                    results_count=0,
                    status="FAILED",
                    error_msg=str(e),
                )
            except Exception:
                pass

        # Rate limiting (PRD §3)
        if i < len(queries_to_run):
            delay = rate_limit(GMAPS_DELAY_SECONDS)
            log.info(f"  Delay: {delay:.1f}s")

    log.info(f"Selesai: {len(all_results)} listings ditemukan total")
    return all_results


# ─── Post-processing & Scoring ───────────────────────────────────────────────
def process_leads(raw_results: list[dict]) -> list[dict]:
    """
    Process raw Google Maps results menjadi scored leads dengan:
    1. Franchise filter (blokir waralaba nasional 100%)
    2. Cross-platform matching (jejak digital 360 derajat)
    3. Auto-detect kategori dan hitung skor prospek
    """
    processed = []
    blocked_count = 0
    
    for r in raw_results:
        nama = r.get("nama_bisnis", "")
        
        if is_national_franchise(nama):
            blocked_count += 1
            log.debug(f"BLOCKED franchise: {nama}")
            continue
        
        kategori = detect_category(nama, r.get("kategori", ""))
        r["kategori_kode"] = kategori

        reviews = r.get("jumlah_review", 0)
        query = r.get("query_used", "").lower()
        is_new = reviews <= 25 or "baru" in query

        alamat = r.get("alamat", "")
        near_rv = is_near_rv(alamat, nama, query)

        lead = {
            "nama_bisnis": nama,
            "kategori": kategori,
            "telepon": r.get("telepon", ""),
            "website": r.get("website", ""),
            "instagram": "",
            "rating": r.get("rating", 0),
            "is_new_3months": is_new,
            "is_new_6months": False,
            "lokasi_dekat_rv": near_rv,
            "lokasi_makassar_kota": "makassar" in (alamat + " " + query).lower(),
        }

        scored = score_and_format(lead)
        r["skor"] = scored["skor"]
        r["skor_label"] = scored["skor_label"]
        r["skor_reasons"] = scored["skor_reasons"]
        r["no_whatsapp"] = scored.get("no_whatsapp", "")
        r["whatsapp_link"] = scored.get("whatsapp_link", "")
        r["is_wa_ready"] = scored.get("is_wa_ready", False)
        r["tier_bisnis"] = scored.get("tier_bisnis", "Tier 2")
        r["klaster_wilayah"] = scored.get("klaster_wilayah", "Makassar")

        kebutuhan_map = {
            "property": "Brosur lipat 3 mewah, booklet site plan, roll banner pameran, map serah terima kunci",
            "emas_jewelry": "Kartu garansi/sertifikat emas, amplop nota eksklusif, box perhiasan kustom, paperbag mini premium",
            "kantor_agensi": "Kop surat resmi, map folder company profile, kartu nama staf, ID card lanyard, stempel flash",
            "klinik_estetika": "Kartu member gold foil, brosur pricelist treatment, stiker botol/pot krim vinyl tahan air, paperbag klinik",
            "fashion_butik": "Hang tag label pakaian tebal (doff/glossy), thank you card, stiker segel box, paperbag belanja",
            "fnb": "Buku menu hardcover anti-air, stiker label cup/botol cutting die-cut, kemasan lunch box kustom, table tent QRIS",
            "eo": "Undangan eksklusif hardcover, backdrop photobooth, wristband tiket gelang event, booklet rundown acara",
            "pendidikan": "Brosur PPDB siswa baru, map ijazah/sertifikat tebal, kalender dinding, banner spanduk pendaftaran",
            "retail": "Stiker label kemasan, paperbag belanja, nota rangkap kustom, roll banner promosi",
            "percetakan": "-",
            "lainnya": "Banner promosi, brosur kilat, kartu nama, stempel flash",
        }
        r["proyeksi_kebutuhan"] = kebutuhan_map.get(kategori, "Banner promosi & media cetak")

        pemicu = f"Bisnis terdaftar di koridor {alamat.split(',')[0] if ',' in alamat else 'Makassar'}"
        if is_new:
            pemicu = f"Bisnis baru di {alamat.split(',')[0] if ',' in alamat else 'Makassar'} - potensi tinggi butuh branding awal"
        elif near_rv:
            pemicu = f"Lokasi dekat workshop Bua Kana - peluang servis kilat same-day"

        r["platform_sumber"] = "Google Maps"
        r["url_sumber"] = r.get("url_gmaps", "") or r.get("gmaps_url", "")
        r["pemicu_kebutuhan"] = pemicu
        r["rekomendasi_produk"] = r["proyeksi_kebutuhan"]

        processed.append(r)
    
    if blocked_count > 0:
        log.info(f"Franchise filter: {blocked_count} waralaba nasional diblokir")

    processed.sort(key=lambda x: x.get("skor", 0), reverse=True)
    return processed


HEADERS_RADAR_PROSPEK = [
    "Nama Bisnis", "Kategori", "Sumber Platform", "Skor", "Status",
    "No. WhatsApp", "Link WA", "Proyeksi Kebutuhan Cetak", "Pemicu Kebutuhan & Konteks",
    "Alamat", "Rating & Ulasan", "Website", "Link Sumber Asli", "Tanggal"
]

HEADERS_MARKET_SIGNALS = [
    "Sinyal / Tren Produk", "Platform", "Tingkat Demand",
    "Peluang untuk RUANG VISUAL", "Link Referensi", "Tanggal"
]


def format_wa_hyperlink(phone: str) -> str:
    from scrapers.contact_enricher import classify_phone_number
    info = classify_phone_number(phone)
    return info["wa_link"]


def format_source_hyperlink(url: str, platform: str = "", nama_bisnis: str = "", alamat: str = "") -> str:
    if not url and platform == "Google Maps" and nama_bisnis:
        query = f"{nama_bisnis} {alamat} Makassar".strip()
        url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query)}"
    if not url or url == "-":
        return "-"
    url_lower = url.lower()
    label = "Buka Tautan"
    if "gofood" in url_lower:
        label = "Buka Menu GoFood"
    elif "grab" in url_lower:
        label = "Buka Menu GrabFood"
    elif "facebook.com" in url_lower:
        label = "Buka Listing FB"
    elif "instagram.com" in url_lower:
        label = "Buka Profil IG"
    elif "threads.net" in url_lower:
        label = "Buka Threads"
    elif "google.com/maps" in url_lower or "maps.google" in url_lower:
        label = "Buka Peta"
    elif "tiktok.com" in url_lower:
        label = "Buka TikTok"
    return f'=HYPERLINK("{url}", "{label}")'


def format_gmaps_hyperlink(url: str, nama_bisnis: str = "", alamat: str = "") -> str:
    return format_source_hyperlink(url, "Google Maps", nama_bisnis, alamat)


def format_web_hyperlink(url: str) -> str:
    if not url or url == "-" or not url.startswith("http"):
        return "-"
    return f'=HYPERLINK("{url}", "Buka Web")'


# ─── Export to Google Sheets ──────────────────────────────────────────────────
def export_leads_to_sheet(leads: list[dict], action: str = "append"):
    """Export processed leads ke sheet 'Radar Prospek' dengan format 14 kolom."""
    if not leads:
        log.info("Tidak ada leads baru untuk di-export.")
        return

    rows = []
    for lead in leads:
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
            "percetakan": "Percetakan",
            "lainnya": "Lainnya",
        }.get(lead.get("kategori_kode", ""), "Lainnya")

        phone = lead.get("no_whatsapp", "") or lead.get("telepon", "").strip()
        wa_url = lead.get("whatsapp_link")
        if wa_url:
            wa_link = f'=HYPERLINK("{wa_url}", "Chat WA")'
        else:
            wa_link = format_wa_hyperlink(phone)

        kebutuhan = lead.get("proyeksi_kebutuhan") or lead.get("rekomendasi_produk") or "Banner dan Media Promosi"
        pemicu = lead.get("pemicu_kebutuhan", "-")
        rating_str = f"{lead.get('rating', 0)} ({lead.get('jumlah_review', 0)} ulasan)"
        
        source_url = lead.get("url_gmaps", "") or lead.get("url_sumber", "")
        source_link = format_gmaps_hyperlink(source_url, lead.get("nama_bisnis", ""), lead.get("alamat", ""))
        web_link = format_web_hyperlink(lead.get("website", ""))

        row = [
            lead.get("nama_bisnis", ""),
            kategori_label,
            lead.get("platform_sumber", "Google Maps"),
            str(lead.get("skor", 7)),
            lead.get("skor_label", "WARM"),
            phone or "-",
            wa_link,
            kebutuhan,
            pemicu,
            lead.get("alamat", "-") or "-",
            rating_str,
            web_link,
            source_link,
            lead.get("scrape_date", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Radar Prospek", rows, action=action)
        log.info(f"{len(rows)} leads berhasil di-export ke 'Radar Prospek'")
    except Exception as e:
        log.warning(f"Belum bisa export ke Google Sheets: {e}")
        log.info("Data tetap aman tersimpan di folder data/processed/")
    except Exception as e:
        log.warning(f"Belum bisa export ke Google Sheets: {e}")
        log.info("Data tetap aman tersimpan di folder data/processed/")


def export_trends_to_sheet(trends: list[dict]):
    """Export market signal trends ke sheet 'Market Signals'."""
    if not trends:
        log.info("Tidak ada trends baru untuk di-export")
        return

    rows = []
    for item in trends:
        nama = item.get("nama_bisnis", "")
        kategori = item.get("kategori", "kemasan")
        signal = f"Toko {kategori}: {nama}"
        tingkat_demand = f"Rating {item.get('rating', 0)} ({item.get('jumlah_review', 0)} ulasan)"
        peluang = f"Supplier bahan printing & kemasan di {item.get('alamat', 'Makassar')}. Potensi efisiensi biaya."
        link_ref = item.get("url_gmaps") or f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(nama + ' Makassar')}"

        row = [
            signal,
            "Google Maps",
            tingkat_demand,
            peluang,
            f'=HYPERLINK("{link_ref}"; "Buka Maps")',
            today_wita(),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Market Signals", rows, action="append", headers=HEADERS_MARKET_SIGNALS)
        log.info(f"{len(rows)} trends berhasil di-export ke 'Market Signals'")
    except Exception as e:
        log.warning(f"Belum bisa export ke Google Sheets: {e}")
        log.info("Data tetap aman tersimpan di folder data/processed/")


def export_competitors_to_sheet(competitors: list[dict]):
    """Export competitor data ke sheet 'Matriks Kompetitor'."""
    if not competitors:
        log.info("Tidak ada kompetitor baru untuk di-export")
        return

    rows = []
    for comp in competitors:
        row = [
            comp.get("nama_bisnis", ""),        # A: Nama Kompetitor
            "Digital printing & percetakan",    # B: Fokus Layanan Utama
            "",                                  # C: Celah Kualitas (Module F)
            "",                                  # D: Celah SOP/Admin (Module F)
            f"{comp.get('jumlah_review', 0)} review, rating {comp.get('rating', 0)}",  # E: Estimasi Kapasitas
            "",                                  # F: Estetika Visual (Module C)
            str(comp.get("rating", "")),         # G: Rating GMaps
            str(comp.get("jumlah_review", "")),  # H: Jumlah Review
            "",                                  # I: Akun Instagram (Module C)
            comp.get("website", ""),             # J: Website
            "",                                  # K: Harga Referensi
            comp.get("scrape_date", today_wita()),  # L: Tanggal Update
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Matriks Kompetitor", rows)
        log.info(f"{len(rows)} kompetitor di-export ke 'Matriks Kompetitor'")
    except Exception as e:
        log.warning(f"[WARNING] Belum bisa export ke Google Sheets: {e}")
        log.info("Data tetap aman tersimpan di folder data/processed/")


# ─── CLI Entry Point ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="RUANG VISUAL - Google Maps Scraper (Module B)"
    )
    parser.add_argument(
        "--mode",
        choices=["leads", "competitors", "trends", "all"],
        default="leads",
        help="Mode scraping: leads (calon customer), competitors, trends (market signals), atau all",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit jumlah queries yang diproses (default: semua)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya scrape dan simpan JSON, tidak export ke Google Sheets",
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("RUANG VISUAL - Google Maps Scraper")
    log.info(f"   Mode: {args.mode} | Limit: {args.limit or 'semua'}")
    log.info("=" * 60)

    if args.mode in ("leads", "all"):
        log.info("\nSCRAPING LEADS...")
        raw_leads = scrape_gmaps(GMAPS_LEAD_QUERIES, max_queries=args.limit, mode="leads")

        if raw_leads:
            raw_path = save_raw_json(raw_leads, "gmaps_leads")
            log.info(f"Raw data disimpan: {raw_path}")

            processed = process_leads(raw_leads)
            leads_only = [l for l in processed if l.get("kategori_kode") != "percetakan"]
            from scrapers.utils import deduplicate_leads
            clean_leads, dup_count = deduplicate_leads(leads_only)
            log.info(f"Deduplikasi Leads: {len(clean_leads)} baru, {dup_count} duplikat disaring")

            if clean_leads:
                proc_path = PROCESSED_DIR / f"leads_scored_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
                with open(proc_path, "w", encoding="utf-8") as f:
                    json.dump(clean_leads, f, ensure_ascii=False, indent=2)
                log.info(f"Processed & scored data disimpan: {proc_path}")

                if not args.dry_run:
                    export_leads_to_sheet(clean_leads)
                else:
                    log.info(f"[DRY RUN] {len(clean_leads)} leads baru siap di-export:")
                    for l in clean_leads[:5]:
                        log.info(f"  -> {l['nama_bisnis']} | Skor: {l['skor']}/10 ({l['skor_label']}) | Alamat: {l.get('alamat')}")
            else:
                log.info("Semua prospek yang ditemukan sudah ada di database riwayat (0 prospek baru).")

    if args.mode in ("competitors", "all"):
        log.info("\nSCRAPING COMPETITORS...")
        raw_competitors = scrape_gmaps(
            GMAPS_COMPETITOR_QUERIES, max_queries=args.limit, mode="competitors"
        )

        if raw_competitors:
            raw_path = save_raw_json(raw_competitors, "gmaps_competitors")
            log.info(f"Raw data disimpan: {raw_path}")

            proc_path = PROCESSED_DIR / f"competitors_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(proc_path, "w", encoding="utf-8") as f:
                json.dump(raw_competitors, f, ensure_ascii=False, indent=2)
            log.info(f"Competitors data disimpan: {proc_path}")

            if not args.dry_run:
                export_competitors_to_sheet(raw_competitors)
            else:
                log.info(f"[DRY RUN] {len(raw_competitors)} kompetitor siap di-export:")
                for c in raw_competitors[:5]:
                    log.info(f"  -> {c['nama_bisnis']} | Rating: {c['rating']} ({c['jumlah_review']} ulasan) | Alamat: {c.get('alamat')}")

    if args.mode in ("trends", "all"):
        log.info("\nSCRAPING TRENDS (Market Signals)...")
        raw_trends = scrape_gmaps(
            GMAPS_TREND_QUERIES, max_queries=args.limit, mode="trends"
        )

        if raw_trends:
            raw_path = save_raw_json(raw_trends, "gmaps_trends")
            log.info(f"Raw data disimpan: {raw_path}")

            proc_path = PROCESSED_DIR / f"trends_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(proc_path, "w", encoding="utf-8") as f:
                json.dump(raw_trends, f, ensure_ascii=False, indent=2)
            log.info(f"Trends data disimpan: {proc_path}")

            if not args.dry_run:
                export_trends_to_sheet(raw_trends)
            else:
                log.info(f"[DRY RUN] {len(raw_trends)} trends siap di-export:")
                for t in raw_trends[:5]:
                    log.info(f"  -> {t.get('nama_bisnis')} | {t.get('kategori')} | Rating: {t.get('rating')} ({t.get('jumlah_review')} ulasan)")

    log.info("\nSelesai.")


if __name__ == "__main__":
    main()
