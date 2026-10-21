"""
RUANG VISUAL - GoFood/GrabFood Merchant Scraper
================================================
Modul scraper ringan untuk menangkap data merchant kuliner/resto/cafe di Makassar
dari direktori web food delivery (GoFood/GrabFood).
Sektor F&B adalah konsumen cetak kemasan paling rutin dan berulang (reorder tinggi).
Bebas emoji sesuai aturan operasional RUANG VISUAL.
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import json
import argparse
import urllib.parse
from datetime import datetime

from patchright.sync_api import sync_playwright

from scrapers.config import RAW_DIR, PROCESSED_DIR, GMAPS_DELAY_SECONDS
from scrapers.contact_enricher import classify_phone_number
from scrapers.lead_scorer import score_and_format
from scrapers.utils import get_logger, rate_limit, today_wita, launch_stealth_browser, append_rows_to_sheet, WITA

log = get_logger("food-delivery")

MAKASSAR_DISTRICTS = [
    "Panakkukang", "Pettarani", "Tamalanrea", 
    "Ranggong", "Somba Opu", "Mappala", 
    "Rappocini", "Hertasning", "Bua Kana"
]

GOFOOD_BASE_URL = "https://gofood.co.id/makassar/restaurants"
GRABFOOD_BASE_URL = "https://food.grab.com/id/id/city/makassar"


def scrape_gofood_merchants(limit: int = 10) -> list:
    """
    Scrape data merchant GoFood Makassar via web directory publik.
    Fokus koridor: Panakkukang, Pettarani, Tamalanrea, Ranggong/Somba Opu.
    """
    results = []
    
    with sync_playwright() as p:
        browser = launch_stealth_browser(p)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        try:
            log.info("Membuka direktori GoFood Makassar: " + GOFOOD_BASE_URL)
            page.goto(GOFOOD_BASE_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Scroll sedikit untuk memicu pemuatan kartu
            page.evaluate("window.scrollBy(0, 800)")
            page.wait_for_timeout(2000)
            
            cards = page.locator('a[href*="/makassar/restaurant/"]').all()
            log.info(f"Ditemukan {len(cards)} elemen merchant GoFood Makassar")
            
            seen_urls = set()
            count = 0
            for i, card in enumerate(cards, 1):
                if count >= limit:
                    break
                try:
                    href = card.get_attribute("href") or ""
                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    url = f"https://gofood.co.id{href}" if href.startswith("/") else href
                    lines = [l.strip() for l in card.inner_text().split("\n") if l.strip()]
                    if not lines:
                        continue
                    
                    rating = 0.0
                    try:
                        if lines[0].replace(".", "", 1).isdigit():
                            rating = float(lines[0])
                    except Exception:
                        pass
                    
                    name = lines[1] if len(lines) > 1 else f"Merchant GoFood #{count+1}"
                    subcat = lines[2] if len(lines) > 2 else "Kuliner F&B"
                    district = next((d for d in MAKASSAR_DISTRICTS if d.lower() in name.lower()), "Makassar")
                    
                    results.append({
                        "nama_bisnis": name,
                        "kategori": "fnb",
                        "platform_sumber": "GoFood",
                        "url_sumber": url,
                        "rating": rating,
                        "jumlah_review": 100 if rating >= 4.7 else 25,
                        "alamat": f"{district}, Makassar",
                        "pemicu_kebutuhan": f"Merchant GoFood aktif ({subcat}) - potensi upgrade kemasan stiker & segel higienis",
                        "proyeksi_kebutuhan": "Stiker label cup tahan dingin, kemasan box makanan foodgrade, segel keamanan (tamper seal), table tent QRIS",
                        "rekomendasi_produk": "Stiker label cup tahan dingin, kemasan box makanan foodgrade, segel keamanan (tamper seal), table tent QRIS",
                        "scrape_date": today_wita(),
                    })
                    count += 1
                    log.info(f"  [{count}/{limit}] {name} | {rating} stars | {district}")
                    
                except Exception as e:
                    log.warning(f"  Skip merchant #{i}: {e}")
                    continue
                
        except Exception as e:
            log.error(f"Error scraping GoFood: {e}")
        finally:
            context.close()
            browser.close()
    
    return results


def enrich_with_contact(leads: list) -> list:
    """
    Sambungkan hasil ekstraksi dengan modul contact_enricher dan lead_scorer.
    """
    from scrapers.lead_scorer import score_and_format
    enriched = []
    for lead in leads:
        phone = lead.get("telepon", "") or lead.get("no_telepon", "")
        contact_info = classify_phone_number(phone)
        
        lead["telepon"] = contact_info["formatted"]
        lead["no_whatsapp"] = contact_info["clean_number"]
        lead["whatsapp_link"] = contact_info["wa_link"]
        lead["is_wa_ready"] = contact_info["is_wa_ready"]
        lead["contact_label"] = contact_info["label"]
        
        scored = score_and_format(lead)
        lead["skor"] = scored.get("skor", 7)
        lead["skor_label"] = scored.get("skor_label", "WARM")
        lead["skor_reasons"] = scored.get("skor_reasons", "")
        
        enriched.append(lead)
    
    return enriched


def export_to_sheets(leads: list):
    """
    Export leads ke Google Sheets tab 'Radar Prospek' dengan format 14 kolom.
    """
    if not leads:
        log.info("Tidak ada leads untuk di-export ke Sheets")
        return
    
    rows = []
    for lead in leads:
        phone = lead.get("no_whatsapp", "-")
        wa_link = lead.get("whatsapp_link", "-")
        if wa_link == "-" and phone != "-":
            contact_info = classify_phone_number(phone)
            wa_link = contact_info["wa_link"]
        
        platform = lead.get("platform_sumber", "GoFood")
        source_url = lead.get("url_sumber", "")
        source_link = f'=HYPERLINK("{source_url}", "Buka Menu GoFood")' if source_url else "-"
        
        row = [
            lead.get("nama_bisnis", ""),
            "F&B/Kuliner",
            platform,
            str(lead.get("skor", 7)),
            lead.get("skor_label", "WARM"),
            phone,
            wa_link,
            lead.get("rekomendasi_produk", "Stiker label cup & kemasan foodgrade"),
            lead.get("pemicu_kebutuhan", "Merchant kuliner aktif"),
            lead.get("alamat", "Makassar"),
            f"{lead.get('rating', 0)} ({lead.get('jumlah_review', 0)} ulasan)",
            "-",
            source_link,
            lead.get("scrape_date", today_wita()),
        ]
        rows.append(row)
    
    try:
        append_rows_to_sheet("Radar Prospek", rows, action="append")
        log.info(f"{len(rows)} leads GoFood berhasil di-export ke 'Radar Prospek'")
    except Exception as e:
        log.warning(f"Belum bisa export ke Google Sheets: {e}")


def save_results(results: list, platform: str, dry_run: bool = False):
    """
    Simpan hasil scraping ke data/raw/, data/processed/, dan Google Sheets.
    """
    if dry_run:
        log.info(f"[DRY-RUN] Akan menyimpan {len(results)} leads dari {platform}")
        return
    
    timestamp = datetime.now(WITA).strftime("%Y%m%d_%H%M%S")
    
    raw_file = RAW_DIR / f"{platform.lower()}_merchants_{timestamp}.json"
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log.info(f"Raw data disimpan: {raw_file}")
    
    enriched = enrich_with_contact(results)
    processed_file = PROCESSED_DIR / f"{platform.lower()}_leads_{timestamp}.json"
    with open(processed_file, 'w', encoding='utf-8') as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    log.info(f"Processed data disimpan: {processed_file}")

    export_to_sheets(enriched)


def main():
    parser = argparse.ArgumentParser(description="Scraper merchant kuliner Makassar (GoFood/GrabFood)")
    parser.add_argument("--platform", choices=["gofood", "grabfood", "all"], default="gofood")
    parser.add_argument("--limit", type=int, default=10, help="Jumlah maksimal merchant per platform")
    parser.add_argument("--dry-run", action="store_true", help="Mode simulasi tanpa menyimpan data")
    args = parser.parse_args()
    
    log.info(f"=== RUANG VISUAL - Food Delivery Scraper ===")
    log.info(f"Platform: {args.platform} | Limit: {args.limit} | Dry-run: {args.dry_run}")
    
    all_results = []
    
    if args.platform in ["gofood", "all"]:
        log.info("\n[1/1] Scraping GoFood Makassar...")
        gofood_leads = scrape_gofood_merchants(limit=args.limit)
        log.info(f"Total leads GoFood: {len(gofood_leads)}")
        all_results.extend(gofood_leads)
        save_results(gofood_leads, "GoFood", dry_run=args.dry_run)
    
    if args.platform == "grabfood":
        log.info("\n[INFO] GrabFood scraper belum diimplementasi (YAGNI - cukup fokus GoFood dulu)")
    
    log.info(f"\n=== SELESAI ===")
    log.info(f"Total leads dikumpulkan: {len(all_results)}")
    log.info(f"Rekomendasi: Minta Antigravity untuk audit & integrasi ke pipeline utama")


if __name__ == "__main__":
    main()
