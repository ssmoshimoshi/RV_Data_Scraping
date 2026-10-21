"""
RUANG VISUAL — Facebook Marketplace Scraper (Makassar)
======================================================
Modul untuk mengekstraksi data Facebook Marketplace area Makassar:
1. Prospek: Penjual makanan/kuliner, frozen food, hampers, dan produk fisik yang butuh stiker/kemasan.
2. Kompetitor: Penawaran jasa percetakan/sablon/banner di Marketplace beserta patokan harganya.
3. Market Signals: Tren produk terlaris dan rentang harga pasar di Makassar.

Bekerja secara publik tanpa login Facebook (zero ban risk).
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
    FB_MARKETPLACE_BASE_URL,
    FB_LEAD_QUERIES,
    FB_COMPETITOR_QUERIES,
    FB_DELAY_SECONDS,
    FB_MAX_ITEMS_PER_SESSION,
    RAW_DIR,
    PROCESSED_DIR,
)
from scrapers.lead_scorer import (
    detect_category,
    calculate_score,
    get_score_label,
    is_near_rv,
)
from scrapers.franchise_filter import is_national_franchise
from scrapers.utils import (
    get_logger,
    rate_limit,
    today_wita,
    append_rows_to_sheet,
    get_existing_names,
    launch_stealth_browser,
    WITA,
)

log = get_logger("fb-marketplace")

HEADERS_RADAR_PROSPEK = [
    "Nama Bisnis", "Kategori", "Sumber Platform", "Skor", "Status",
    "No. WhatsApp", "Link WA", "Proyeksi Kebutuhan Cetak", "Pemicu Kebutuhan & Konteks",
    "Alamat", "Rating & Ulasan", "Website", "Link Sumber Asli", "Tanggal"
]

HEADERS_MATRIKS_KOMPETITOR = [
    "Nama Percetakan", "Fokus Layanan Utama", "Kapasitas / Skala",
    "Rating & Ulasan", "No. WhatsApp", "Link WA", "Celah Kualitas",
    "Celah Pelayanan & SOP", "Selling Point RUANG VISUAL", "Website / Maps", "Tanggal Update"
]

HEADERS_MARKET_SIGNALS = [
    "Signal", "Platform", "Metrik", "Relevansi", "URL", "Tanggal"
]


def format_link_hyperlink(url: str, label: str = "Buka Link") -> str:
    """Format URL menjadi formula Google Sheets HYPERLINK."""
    if not url or url.strip() == "-":
        return "-"
    clean = url.strip()
    return f'=HYPERLINK("{clean}"; "{label}")'


def project_fb_lead_needs(title: str, category: str) -> str:
    """Proyeksikan kebutuhan cetak spesifik untuk penjual di FB Marketplace."""
    t_lower = title.lower()
    if any(k in t_lower for k in ["kue", "cake", "roti", "bakery", "snack"]):
        return "Stiker Label Toples Tahan Minyak, Box Kraft Packaging, Thank You Card"
    elif any(k in t_lower for k in ["frozen", "beku", "nugget", "dimsum", "bakso"]):
        return "Stiker Vinyl Waterproof (Tahan Suhu Freezer), Vacuum Bag Packaging"
    elif any(k in t_lower for k in ["catering", "nasi", "tumpeng", "kotak", "box"]):
        return "Paper Lunch Box Custom Logo, Dus Nasi Sablon, Stiker Segel Kemasan"
    elif any(k in t_lower for k in ["hampers", "gift", "kado", "souvenir"]):
        return "Hardbox Eksklusif, Greeting Card Lipat, Pita Sablon Logo, Hangtag"
    elif any(k in t_lower for k in ["butik", "hijab", "baju", "gamis", "fashion"]):
        return "Hangtag Tebal Ivory 310gsm, Polymailer Custom Logo, Stiker Barcode"
    elif any(k in t_lower for k in ["skincare", "lotion", "cream", "sabun"]):
        return "Label Botol Kosmetik Hologram / Transparan, Box Inner Skincare"
    else:
        return "Stiker Kemasan Produk, Banner Display Toko, Kartu Ucapan Terima Kasih"


def scrape_marketplace_query(page, query: str, limit: int = 15) -> list[dict]:
    """Scrape daftar barang di FB Marketplace Makassar berdasarkan kata kunci."""
    encoded_q = urllib.parse.quote(query)
    target_url = f"{FB_MARKETPLACE_BASE_URL}{encoded_q}"
    log.info(f"Membuka FB Marketplace: {target_url}")

    results = []
    try:
        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Tutup modal login jika muncul
        try:
            close_buttons = page.locator('div[role="dialog"] [aria-label="Close"], div[aria-label="Tutup"]').all()
            for btn in close_buttons:
                if btn.is_visible():
                    btn.click()
                    time.sleep(1)
        except Exception:
            pass

        # Scroll 2-3 kali untuk memuat lebih banyak listing
        for _ in range(3):
            page.mouse.wheel(0, 1500)
            time.sleep(1.5)

        # Ambil link marketplace
        links = page.locator('a[href*="/marketplace/item/"]').all()
        log.info(f"Ditemukan {len(links)} elemen listing untuk query '{query}'")

        seen_urls = set()
        for link in links:
            if len(results) >= limit:
                break
            try:
                href = link.get_attribute("href") or ""
                if not href or "/marketplace/item/" not in href:
                    continue

                full_url = href if href.startswith("http") else f"https://www.facebook.com{href}"
                item_id = href.split("/marketplace/item/")[1].split("/")[0].split("?")[0]
                canonical_url = f"https://www.facebook.com/marketplace/item/{item_id}/"

                if canonical_url in seen_urls:
                    continue
                seen_urls.add(canonical_url)

                text_content = link.inner_text().strip()
                lines = [line.strip() for line in text_content.split("\n") if line.strip()]

                price = "Rp 0"
                title = query.title()
                location = "Makassar"

                if lines:
                    for line in lines:
                        if "Rp" in line or line.lower().startswith("gratis"):
                            price = line
                            break

                    non_price_lines = [l for l in lines if "Rp" not in l and not l.lower().startswith("gratis")]
                    if non_price_lines:
                        title = non_price_lines[0]
                    if len(non_price_lines) > 1:
                        location = non_price_lines[-1]

                results.append({
                    "id": item_id,
                    "title": title,
                    "price": price,
                    "location": location,
                    "url": canonical_url,
                    "query": query,
                    "raw_text": " | ".join(lines),
                    "scrape_date": today_wita(),
                })
            except Exception as e:
                continue

    except Exception as e:
        log.error(f"Gagal memuat Marketplace untuk query '{query}': {e}")

    return results


def process_fb_leads(items: list[dict]) -> list[dict]:
    """Proses listing produk menjadi calon prospek percetakan RUANG VISUAL."""
    leads = []
    for item in items:
        title = item["title"]
        if is_national_franchise(title):
            log.debug(f"BLOCKED franchise: {title}")
            continue

        location = item.get("location", "Makassar")
        cat = detect_category(title, bio=item.get("raw_text", ""))
        if cat == "lainnya":
            cat = "fnb"

        needs = project_fb_lead_needs(title, cat)
        near_rv = is_near_rv(location, name=title)
        pemicu = f"Listing produk aktif FB Marketplace {location} - potensi kebutuhan upgrade kemasan profesional"

        lead = {
            "nama_bisnis": f"{title} (Seller FB)",
            "kategori": cat,
            "kategori_kode": cat,
            "telepon": "",
            "website": "",
            "instagram": "",
            "lokasi_dekat_rv": near_rv,
            "lokasi_makassar_kota": True,
            "proyeksi_kebutuhan": needs,
            "alamat": f"{location}, Makassar",
            "rating": 4.5,
            "jumlah_review": 1,
            "url_referensi": item["url"],
            "harga_produk": item.get("price", "-"),
            "scrape_date": item.get("scrape_date", today_wita()),
            "platform_sumber": "Facebook Marketplace",
            "url_sumber": item["url"],
            "pemicu_kebutuhan": pemicu,
            "rekomendasi_produk": needs,
        }

        score, reasons = calculate_score(lead)
        lead["skor"] = score
        lead["skor_label"] = get_score_label(score)
        lead["skor_reasons"] = "; ".join(reasons)
        leads.append(lead)

    return leads


def process_fb_competitors(items: list[dict]) -> list[dict]:
    """Proses listing percetakan menjadi data Matriks Kompetitor."""
    competitors = []
    for item in items:
        title = item["title"]
        price = item.get("price", "-")
        location = item.get("location", "Makassar")

        fokus = "Jasa Cetak & Advertising"
        if "banner" in title.lower() or "spanduk" in title.lower():
            fokus = "Cetak Banner & Spanduk Outdoor"
        elif "stiker" in title.lower():
            fokus = "Cetak Stiker Label & A3+"
        elif "undangan" in title.lower():
            fokus = "Cetak Undangan Pernikahan"
        elif "nota" in title.lower():
            fokus = "Cetak Nota / Bon NCR"

        comp = {
            "nama_bisnis": f"{title} (Vendor FB)",
            "fokus_layanan": fokus,
            "estimasi_kapasitas": f"Listing Marketplace ({price})",
            "rating_gmaps": "4.0",
            "jumlah_review": "5",
            "telepon": "",
            "celah_kualitas": "Kualitas warna dan ketebalan bahan belum terstandarisasi industri",
            "celah_sop": "Transaksi via chat personal rawan salah ukuran dan tidak tepat waktu",
            "selling_point_rv": "Standar korporat, proofing warna akurat, jaminan pengerjaan tepat waktu, workshop fisik jelas",
            "url": item["url"],
            "tanggal_update": today_wita(),
        }
        competitors.append(comp)
    return competitors


def process_fb_trends(lead_items: list[dict], comp_items: list[dict]) -> list[dict]:
    """Formulasikan sinyal pasar dari dinamika Facebook Marketplace Makassar."""
    signals = []

    if lead_items:
        fnb_count = sum(1 for x in lead_items if any(k in x["title"].lower() for k in ["kue", "snack", "frozen", "catering", "makanan"]))
        if fnb_count > 0:
            signals.append({
                "signal": f"Tingginya Penjualan Kuliner Rumahan & Frozen Food ({fnb_count} listing baru)",
                "platform": "Facebook Marketplace",
                "metrik": f"Volume Tinggi ({fnb_count} Listing)",
                "relevansi": "Peluang penawaran paket stiker toples waterproof dan box kemasan ekonomis",
                "url": "https://www.facebook.com/marketplace/makassar/",
                "tanggal": today_wita(),
            })

        fashion_count = sum(1 for x in lead_items if any(k in x["title"].lower() for k in ["baju", "hijab", "gamis", "butik"]))
        if fashion_count > 0:
            signals.append({
                "signal": f"Aktivitas Penjual Fashion Muslim & Butik Makassar ({fashion_count} listing)",
                "platform": "Facebook Marketplace",
                "metrik": f"Trend Menengah ({fashion_count} Listing)",
                "relevansi": "Kebutuhan hangtag tebal, plastik polymailer bermerek, dan kartu terima kasih",
                "url": "https://www.facebook.com/marketplace/makassar/",
                "tanggal": today_wita(),
            })

    if comp_items:
        prices = [x.get("price", "") for x in comp_items if "Rp" in x.get("price", "")]
        sample_price = prices[0] if prices else "Rp 15.000 - Rp 25.000"
        signals.append({
            "signal": "Perang Harga Percetakan Spanduk & Stiker di Marketplace Makassar",
            "platform": "Facebook Marketplace",
            "metrik": f"Benchmark Pasar: {sample_price}",
            "relevansi": "RUANG VISUAL tidak boleh sekadar bersaing murah, wajib tonjolkan ketajaman warna dan ketahanan bahan outdoor",
            "url": "https://www.facebook.com/marketplace/makassar/",
            "tanggal": today_wita(),
        })

    return signals


def export_fb_leads_to_sheet(leads: list[dict]):
    """Export prospek FB Marketplace ke Google Sheets 'Radar Prospek'."""
    if not leads:
        return
    from scrapers.gmaps_scraper import export_leads_to_sheet
    export_leads_to_sheet(leads, action="append")


def export_fb_competitors_to_sheet(competitors: list[dict]):
    """Export kompetitor FB Marketplace ke Google Sheets 'Matriks Kompetitor'."""
    if not competitors:
        return
    rows = []
    for c in competitors:
        row = [
            c.get("nama_bisnis", ""),
            c.get("fokus_layanan", ""),
            c.get("estimasi_kapasitas", ""),
            "Listing Marketplace",
            "-",
            "-",
            c.get("celah_kualitas", "-"),
            c.get("celah_sop", "-"),
            c.get("selling_point_rv", "-"),
            format_link_hyperlink(c.get("url", ""), "Buka Listing FB"),
            c.get("tanggal_update", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Matriks Kompetitor", rows, action="append", headers=HEADERS_MATRIKS_KOMPETITOR)
        log.info(f"{len(rows)} vendor FB Marketplace berhasil diekspor ke 'Matriks Kompetitor'")
    except Exception as e:
        log.warning(f"Gagal export ke Google Sheets: {e}")


def export_fb_signals_to_sheet(signals: list[dict]):
    """Export sinyal pasar FB Marketplace ke Google Sheets 'Market Signals'."""
    if not signals:
        return
    rows = []
    for s in signals:
        row = [
            s.get("signal", ""),
            s.get("platform", "Facebook Marketplace"),
            s.get("metrik", ""),
            s.get("relevansi", ""),
            format_link_hyperlink(s.get("url", ""), "Lihat Marketplace"),
            s.get("tanggal", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Market Signals", rows, action="append", headers=HEADERS_MARKET_SIGNALS)
        log.info(f"{len(rows)} sinyal pasar FB Marketplace berhasil diekspor ke 'Market Signals'")
    except Exception as e:
        log.warning(f"Gagal export ke Google Sheets: {e}")


def main():
    parser = argparse.ArgumentParser(description="RUANG VISUAL — Facebook Marketplace Scraper")
    parser.add_argument("--mode", choices=["leads", "competitors", "trends", "all"], default="all")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("RUANG VISUAL — Facebook Marketplace Scraper (Makassar)")
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

        # 1. Scrape Leads
        if args.mode in ["leads", "all"]:
            for q in FB_LEAD_QUERIES[:3]:  # Ambil 3 query teratas untuk efisiensi
                items = scrape_marketplace_query(page, q, limit=args.limit)
                all_raw_leads.extend(items)
                rate_limit(FB_DELAY_SECONDS)

        # 2. Scrape Competitors
        if args.mode in ["competitors", "all"]:
            for q in FB_COMPETITOR_QUERIES[:3]:
                items = scrape_marketplace_query(page, q, limit=args.limit)
                all_raw_comps.extend(items)
                rate_limit(FB_DELAY_SECONDS)

        browser.close()

    timestamp = datetime.now(WITA).strftime("%Y%m%d_%H%M%S")

    # Simpan data mentah
    if all_raw_leads:
        raw_path = RAW_DIR / f"fb_marketplace_leads_{timestamp}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(all_raw_leads, f, ensure_ascii=False, indent=2)
        log.info(f"Data mentah leads tersimpan: {raw_path}")

    if all_raw_comps:
        raw_path = RAW_DIR / f"fb_marketplace_comps_{timestamp}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(all_raw_comps, f, ensure_ascii=False, indent=2)
        log.info(f"Data mentah kompetitor tersimpan: {raw_path}")

    # Proses & Export
    if all_raw_leads and args.mode in ["leads", "all"]:
        leads = process_fb_leads(all_raw_leads)
        proc_path = PROCESSED_DIR / f"fb_leads_processed_{timestamp}.json"
        with open(proc_path, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)
        log.info(f"Leads FB Marketplace terproses: {len(leads)}")
        if not args.dry_run:
            export_fb_leads_to_sheet(leads)

    if all_raw_comps and args.mode in ["competitors", "all"]:
        comps = process_fb_competitors(all_raw_comps)
        proc_path = PROCESSED_DIR / f"fb_comps_processed_{timestamp}.json"
        with open(proc_path, "w", encoding="utf-8") as f:
            json.dump(comps, f, ensure_ascii=False, indent=2)
        log.info(f"Kompetitor FB Marketplace terproses: {len(comps)}")
        if not args.dry_run:
            export_fb_competitors_to_sheet(comps)

    if args.mode in ["trends", "all"]:
        trends = process_fb_trends(all_raw_leads, all_raw_comps)
        if trends:
            proc_path = PROCESSED_DIR / f"fb_trends_processed_{timestamp}.json"
            with open(proc_path, "w", encoding="utf-8") as f:
                json.dump(trends, f, ensure_ascii=False, indent=2)
            log.info(f"Sinyal pasar FB Marketplace terproses: {len(trends)}")
            if not args.dry_run:
                export_fb_signals_to_sheet(trends)

    log.info("Selesai menjalankan Facebook Marketplace Scraper.")


if __name__ == "__main__":
    main()
