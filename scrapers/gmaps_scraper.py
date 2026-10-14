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
    - Export ke Google Sheets atau simpan lokal di data/raw/ & data/processed/
    - Rate limiting & deduplikasi otomatis
"""

import re
import json
import time
import argparse
import urllib.parse
from datetime import datetime
from pathlib import Path

from patchright.sync_api import sync_playwright

from scrapers.config import (
    GMAPS_LEAD_QUERIES,
    GMAPS_COMPETITOR_QUERIES,
    GMAPS_DELAY_SECONDS,
    RAW_DIR,
    PROCESSED_DIR,
)
from scrapers.lead_scorer import detect_category, score_and_format
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
    """Buat URL pencarian Google Maps."""
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.google.com/maps/search/{encoded}/"


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

    log.info(f"🗺️  Memulai Google Maps scraping ({mode}) — {len(queries_to_run)} queries")

    # Ambil nama yang sudah ada di sheet untuk deduplikasi
    sheet_name = "Radar Prospek" if mode == "leads" else "Matriks Kompetitor"
    try:
        existing = get_existing_names(sheet_name)
        log.info(f"📋 {len(existing)} entri sudah ada di '{sheet_name}'")
    except Exception as e:
        log.info(f"ℹ️  Sheet '{sheet_name}' belum terbaca (akan disimpan lokal): {e}")
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
            log.error(f"  ❌ Error scraping '{query}': {e}")
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
            log.info(f"  ⏳ Delay: {delay:.1f}s")

    log.info(f"🏁 Selesai: {len(all_results)} listings ditemukan total")
    return all_results


# ─── Post-processing & Scoring ───────────────────────────────────────────────
def process_leads(raw_results: list[dict]) -> list[dict]:
    """
    Process raw Google Maps results menjadi scored leads.
    Auto-detect kategori dan hitung skor prospek.
    """
    processed = []
    for r in raw_results:
        kategori = detect_category(r["nama_bisnis"], r.get("kategori", ""))
        r["kategori_kode"] = kategori

        # Bisnis terindikasi baru jika ulasan sedikit (<25) atau query mengandung 'baru'
        reviews = r.get("jumlah_review", 0)
        query = r.get("query_used", "").lower()
        is_new = reviews <= 25 or "baru" in query

        lead = {
            "nama_bisnis": r["nama_bisnis"],
            "kategori": kategori,
            "telepon": r.get("telepon", ""),
            "website": r.get("website", ""),
            "instagram": "",
            "rating": r.get("rating", 0),
            "is_new_3months": is_new,
            "is_new_6months": False,
            "lokasi_makassar_kota": "makassar" in (r.get("alamat", "") + " " + query).lower(),
        }

        scored = score_and_format(lead)
        r["skor"] = scored["skor"]
        r["skor_label"] = scored["skor_label"]
        r["skor_reasons"] = scored["skor_reasons"]

        kebutuhan_map = {
            "fnb": "Packaging box, stiker cup segel, buku menu & banner",
            "eo": "Backdrop panggung, banner promosi, id card, sertifikat",
            "retail": "Stiker label kemasan, paper bag, kartu nama, brosur",
            "instansi": "Buku laporan/agenda, signage, seragam/id card, kop surat",
            "percetakan": "-",
            "lainnya": "Banner promosi, brosur kilat, kartu nama",
        }
        r["proyeksi_kebutuhan"] = kebutuhan_map.get(kategori, "Banner & Media Promosi")

        processed.append(r)

    processed.sort(key=lambda x: x.get("skor", 0), reverse=True)
    return processed


HEADERS_RADAR_PROSPEK = [
    "Nama Bisnis", "Kategori", "Skor", "Status", "No. WhatsApp",
    "Link WA", "Proyeksi Kebutuhan Cetak", "Alamat", "Rating & Ulasan",
    "Website", "Peta Lokasi", "Tanggal"
]


def format_wa_hyperlink(phone: str) -> str:
    if not phone:
        return "-"
    clean = "".join([c for c in phone if c.isdigit()])
    if clean.startswith("08"):
        clean = "62" + clean[1:]
    elif clean.startswith("8"):
        clean = "62" + clean
    return f'=HYPERLINK("https://wa.me/{clean}"; "📲 Chat WA")' if clean else "-"


def format_gmaps_hyperlink(url: str) -> str:
    if not url:
        return "-"
    return f'=HYPERLINK("{url}"; "📍 Buka GMaps")'


# ─── Export to Google Sheets ──────────────────────────────────────────────────
def export_leads_to_sheet(leads: list[dict], action: str = "append"):
    """Export processed leads ke sheet 'Radar Prospek' dengan format eksekutif rapi."""
    if not leads:
        log.info("Tidak ada leads baru untuk di-export")
        return

    rows = []
    for lead in leads:
        kategori_label = {
            "fnb": "F&B",
            "eo": "Event Organizer",
            "retail": "Retail/UMKM",
            "instansi": "Instansi/Kantor",
            "percetakan": "Percetakan",
            "lainnya": "Lainnya",
        }.get(lead.get("kategori_kode", ""), "Lainnya")

        phone = lead.get("telepon", "").strip()
        wa_link = format_wa_hyperlink(phone)
        gmaps_url = lead.get("url_gmaps", "").strip()
        gmaps_link = format_gmaps_hyperlink(gmaps_url)
        kebutuhan = lead.get("proyeksi_kebutuhan", "Banner & Media Promosi")
        rating_str = f"{lead.get('rating', 0)} ⭐ ({lead.get('jumlah_review', 0)} ulasan)"

        row = [
            lead.get("nama_bisnis", ""),         # A: Nama Bisnis
            kategori_label,                       # B: Kategori
            str(lead.get("skor", 7)),             # C: Skor
            lead.get("skor_label", "🟡 WARM"),   # D: Status
            phone or "-",                         # E: No. WhatsApp
            wa_link,                              # F: Link WA
            kebutuhan,                            # G: Proyeksi Kebutuhan Cetak
            lead.get("alamat", "-") or "-",       # H: Alamat
            rating_str,                           # I: Rating & Ulasan
            lead.get("website", "-") or "-",      # J: Website
            gmaps_link,                           # K: Peta Lokasi
            lead.get("scrape_date", today_wita()),# L: Tanggal
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Radar Prospek", rows, action=action, headers=HEADERS_RADAR_PROSPEK)
        log.info(f"📊 {len(rows)} leads berhasil di-export ke 'Radar Prospek'")
    except Exception as e:
        log.warning(f"⚠️  Belum bisa export ke Google Sheets: {e}")
        log.info("ℹ️  Data tetap aman tersimpan di folder data/processed/")


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
        log.info(f"📊 {len(rows)} kompetitor di-export ke 'Matriks Kompetitor'")
    except Exception as e:
        log.warning(f"⚠️  Belum bisa export ke Google Sheets: {e}")
        log.info("ℹ️  Data tetap aman tersimpan di folder data/processed/")


# ─── CLI Entry Point ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="RUANG VISUAL — Google Maps Scraper (Module B)"
    )
    parser.add_argument(
        "--mode",
        choices=["leads", "competitors", "all"],
        default="leads",
        help="Mode scraping: leads (calon customer), competitors, atau all",
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
    log.info("🗺️  RUANG VISUAL — Google Maps Scraper")
    log.info(f"   Mode: {args.mode} | Limit: {args.limit or 'semua'}")
    log.info("=" * 60)

    if args.mode in ("leads", "all"):
        log.info("\n📍 SCRAPING LEADS...")
        raw_leads = scrape_gmaps(GMAPS_LEAD_QUERIES, max_queries=args.limit, mode="leads")

        if raw_leads:
            raw_path = save_raw_json(raw_leads, "gmaps_leads")
            log.info(f"💾 Raw data disimpan: {raw_path}")

            processed = process_leads(raw_leads)
            leads_only = [l for l in processed if l.get("kategori_kode") != "percetakan"]

            proc_path = PROCESSED_DIR / f"leads_scored_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(proc_path, "w", encoding="utf-8") as f:
                json.dump(leads_only, f, ensure_ascii=False, indent=2)
            log.info(f"💾 Processed & scored data disimpan: {proc_path}")

            if not args.dry_run:
                export_leads_to_sheet(leads_only)
            else:
                log.info(f"[DRY RUN] {len(leads_only)} leads siap di-export:")
                for l in leads_only[:5]:
                    log.info(f"  → {l['nama_bisnis']} | Skor: {l['skor']}/10 ({l['skor_label']}) | Alamat: {l.get('alamat')}")

    if args.mode in ("competitors", "all"):
        log.info("\n🏭 SCRAPING COMPETITORS...")
        raw_competitors = scrape_gmaps(
            GMAPS_COMPETITOR_QUERIES, max_queries=args.limit, mode="competitors"
        )

        if raw_competitors:
            raw_path = save_raw_json(raw_competitors, "gmaps_competitors")
            log.info(f"💾 Raw data disimpan: {raw_path}")

            proc_path = PROCESSED_DIR / f"competitors_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(proc_path, "w", encoding="utf-8") as f:
                json.dump(raw_competitors, f, ensure_ascii=False, indent=2)
            log.info(f"💾 Competitors data disimpan: {proc_path}")

            if not args.dry_run:
                export_competitors_to_sheet(raw_competitors)
            else:
                log.info(f"[DRY RUN] {len(raw_competitors)} kompetitor siap di-export:")
                for c in raw_competitors[:5]:
                    log.info(f"  → {c['nama_bisnis']} | Rating: {c['rating']} ({c['jumlah_review']} ulasan) | Alamat: {c.get('alamat')}")

    log.info("\n✅ Selesai!")


if __name__ == "__main__":
    main()
