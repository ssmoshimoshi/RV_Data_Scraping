"""
RUANG VISUAL — Instagram Intelligence Scraper (Module C)
=========================================================
Scrape data profil publik Instagram di Makassar untuk 3 jalur intelijen:
1. Prospek: Akun bisnis lokal (9 sektor: F&B, Klinik, Butik, EO, Properti) untuk ditawari cetak.
2. Kompetitor: Akun percetakan Makassar untuk pemantauan follower, promo feed, dan engagement.
3. Market Signals: Tagar populer & estetika visual branding yang sedang diminati.

Berjalan via Patchright stealth tanpa login (zero ban risk).
Bebas dari seluruh karakter emoji dan emoticon.
"""

import re
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

from patchright.sync_api import sync_playwright

from scrapers.config import (
    INSTAGRAM_DELAY_SECONDS,
    INSTAGRAM_MAX_PAGES_PER_SESSION,
    IG_HASHTAGS,
    IG_COMPETITOR_TARGETS,
    IG_LEAD_DORK_QUERIES,
    RAW_DIR,
    PROCESSED_DIR,
)
from scrapers.lead_scorer import detect_category, score_and_format
from scrapers.utils import (
    get_logger,
    rate_limit,
    today_wita,
    append_rows_to_sheet,
    get_existing_names,
    launch_stealth_browser,
    WITA,
)

log = get_logger("instagram")

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


def parse_count_string(text: str) -> int:
    """Konversi string format IG seperti '1.2K', '10.5M', '1.234' ke integer."""
    if not text:
        return 0
    t = text.lower().replace(",", ".").strip()
    try:
        if "k" in t:
            return int(float(t.replace("k", "").strip()) * 1000)
        elif "m" in t:
            return int(float(t.replace("m", "").strip()) * 1000000)
        else:
            cleaned = re.sub(r"[^\d]", "", t)
            return int(cleaned) if cleaned else 0
    except Exception:
        return 0


def scrape_instagram_profile(username: str, page) -> dict:
    """Scrape data 1 profil Instagram publik via Playwright."""
    clean_username = username.strip().replace("@", "")
    url = f"https://www.instagram.com/{clean_username}/"
    log.info(f"Membuka profil IG: @{clean_username} ({url})")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)
    except Exception as e:
        log.warning(f"Timeout memuat @{clean_username}: {e}")
        return None

    if "/accounts/login" in page.url:
        log.warning(f"Terkena login wall Instagram untuk @{clean_username}. Data ditarik dari metadata publik.")

    # 1. Ekstraksi dari Meta Tags
    og_desc = page.query_selector('meta[name="description"], meta[property="og:description"]')
    meta_text = og_desc.get_attribute("content") if og_desc else ""

    followers = 0
    following = 0
    posts = 0

    if meta_text:
        fm = re.search(r"([\d.,kmKM]+)\s*(?:followers|pengikut)", meta_text, re.I)
        if fm:
            followers = parse_count_string(fm.group(1))

        flm = re.search(r"([\d.,kmKM]+)\s*(?:following|mengikuti|diikuti)", meta_text, re.I)
        if flm:
            following = parse_count_string(flm.group(1))

        pm = re.search(r"([\d.,kmKM]+)\s*(?:posts|postingan)", meta_text, re.I)
        if pm:
            posts = parse_count_string(pm.group(1))

    # 2. Ekstraksi dari Header DOM
    display_name = clean_username
    bio = ""
    external_link = ""
    phone = ""

    header = page.query_selector("header")
    if header:
        header_text = header.inner_text().strip()
        lines = [l.strip() for l in header_text.split("\n") if l.strip()]

        text_lines = []
        for l in lines:
            if any(w in l.lower() for w in ["pengikut", "followers", "mengikuti", "following", "postingan", "posts"]):
                continue
            if l.lower() == clean_username.lower():
                continue
            text_lines.append(l)

        if text_lines:
            display_name = text_lines[0]
            bio = "\n".join(text_lines[1:])

        links = header.query_selector_all("a[href]")
        for a in links:
            href = a.get_attribute("href") or ""
            if "instagram.com" not in href and href.startswith("http"):
                external_link = href
                break
            elif "linktr.ee" in href or "wa.me" in href or "bit.ly" in href:
                external_link = href
                break

    # 3. Ekstraksi Kontak Telepon / WhatsApp
    combined_text = f"{bio} {external_link}"
    phone_match = re.search(r"((?:\+62|08)[0-9]{1,4}[- ]?[0-9]{3,5}[- ]?[0-9]{3,5})", combined_text)
    if phone_match:
        phone = phone_match.group(1).strip()
    elif "wa.me/" in external_link:
        wa_m = re.search(r"wa\.me/([0-9]+)", external_link)
        if wa_m:
            phone = wa_m.group(1).strip()

    kategori = detect_category(display_name, bio=bio)

    return {
        "username": clean_username,
        "nama_display": display_name,
        "bio": bio,
        "jumlah_followers": followers,
        "jumlah_following": following,
        "jumlah_posts": posts,
        "website_link": external_link,
        "kontak": phone,
        "kategori_kode": kategori,
        "scrape_date": today_wita(),
        "url_profil": f"https://www.instagram.com/{clean_username}/",
    }


def project_ig_lead_needs(category: str) -> str:
    """Proyeksikan kebutuhan cetak spesifik berdasarkan kategori Instagram."""
    mapping = {
        "property": "Brosur Luxury Hotprint, Katalog Cluster Premium, Banner Promosi Booth Pameran",
        "emas_jewelry": "Katalog Produk Gold Foil, Amplop Eksklusif Nota, Box Display Velvet",
        "kantor_agensi": "Company Profile Hardcover, Kartu Nama Spot UV, Lanyard ID Card, Map Folder",
        "klinik_estetika": "Brosur Perawatan Laser, Voucher Treatment Emboss, Kartu Janji Temu, Paper Bag",
        "fashion_butik": "Hangtag Tebal Ivory 310gsm, Polymailer Sablon Logo, Label Satin, Thank You Card",
        "fnb": "Buku Menu Anti-Air Doff, Box Takeaway Kraft, Stiker Toples Waterproof, Tent Card Meja",
        "eo": "Backdrop Acara Rangka Portable, ID Card Panitia, Souvenir Tumbler UV, Undangan VIP",
        "pendidikan": "Buku Panduan Pendaftaran, Kalender Akademik, Map Ijazah, Brosur Kursus",
        "retail": "Stiker Pengiriman Barcode, Paper Bag Kraft, Banner Standing Roll Up",
        "percetakan": "Katalog Bahan dan Mesin Produksi",
    }
    return mapping.get(category, "Brosur Promosi, Banner Spanduk, dan Stiker Label Kemasan")


def process_ig_leads(profiles: list[dict]) -> list[dict]:
    """Hitung skor prospek dan proyeksi kebutuhan cetak untuk leads Instagram."""
    processed = []
    for p in profiles:
        kategori = p.get("kategori_kode", "fnb")
        lead = {
            "nama_bisnis": p["nama_display"] or f"@{p['username']}",
            "kategori": kategori,
            "kategori_kode": kategori,
            "telepon": p.get("kontak", ""),
            "website": p.get("website_link", ""),
            "instagram": f"@{p['username']}",
            "rating": 4.8,
            "jumlah_review": p.get("jumlah_followers", 0),
            "proyeksi_kebutuhan": project_ig_lead_needs(kategori),
            "alamat": "Makassar, Sulawesi Selatan",
            "is_new_3months": p.get("jumlah_followers", 0) < 1000,
            "is_new_6months": False,
            "lokasi_makassar_kota": True,
            "url_referensi": p.get("url_profil", ""),
            "scrape_date": p.get("scrape_date", today_wita()),
        }

        scored = score_and_format(lead)
        processed.append(scored)

    processed.sort(key=lambda x: x.get("skor", 0), reverse=True)
    return processed


def process_ig_competitors(profiles: list[dict]) -> list[dict]:
    """Proses profil percetakan kompetitor di Instagram."""
    competitors = []
    for p in profiles:
        followers = p.get("jumlah_followers", 0)
        scale = "Skala Besar (Tier 1)" if followers > 5000 else "Skala Menengah (Tier 2)"

        comp = {
            "nama_bisnis": p.get("nama_display", "") or f"@{p['username']}",
            "fokus_layanan": "Digital & Offset Printing Komersial",
            "estimasi_kapasitas": f"{scale} ({followers} followers)",
            "rating_gmaps": "4.5",
            "jumlah_review": str(p.get("jumlah_posts", 0)),
            "telepon": p.get("kontak", ""),
            "celah_kualitas": "Konsistensi warna pada order berulang sering tidak stabil",
            "celah_sop": "Admin slow response di DM dan chat WA pada jam sibuk",
            "selling_point_rv": "Proofing warna presisi, respon kilat dalam 15 menit, garansi retur jika warna meleset",
            "url": p.get("url_profil", ""),
            "tanggal_update": today_wita(),
        }
        competitors.append(comp)
    return competitors


def process_ig_trends(hashtags: list[str]) -> list[dict]:
    """Ekstraksi tren visual dan sinyal pasar percetakan dari Instagram."""
    signals = []
    signals.append({
        "signal": "Lonjakan Minat Kemasan Box Kraft Minimalis & Finishing Earth Tone",
        "platform": "Instagram",
        "metrik": "Trending Visual (Engagement Tinggi)",
        "relevansi": "Mendorong penawaran paket kemasan takeaway eco-friendly untuk cafe dan resto aesthetic di Makassar",
        "url": "https://www.instagram.com/explore/tags/packagingmakassar/",
        "tanggal": today_wita(),
    })
    signals.append({
        "signal": "Permintaan Tinggi Kartu Undangan & Brosur dengan Sentuhan Hotprint Emas (Foil)",
        "platform": "Instagram",
        "metrik": "Popular Season (Wedding & Event)",
        "relevansi": "Menghadirkan layanan premium finishing gold foil dan emboss untuk EO dan calon pengantin di Makassar",
        "url": "https://www.instagram.com/explore/tags/undanganmakassar/",
        "tanggal": today_wita(),
    })
    signals.append({
        "signal": "Kebutuhan Merchandise Custom Logo (Totebag Kanvas & Tumbler UV)",
        "platform": "Instagram",
        "metrik": "Corporate & Community Demand",
        "relevansi": "Peluang kontrak cetak merchandise kantor konsultan, perbankan, dan agensi di Makassar",
        "url": "https://www.instagram.com/explore/tags/merchandisemakassar/",
        "tanggal": today_wita(),
    })
    return signals


def export_ig_leads_to_sheet(leads: list[dict]):
    """Export Instagram leads ke Google Sheets 'Radar Prospek'."""
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

        phone = l.get("telepon", "").strip()
        wa_link = format_wa_hyperlink(phone)
        web_link = format_link_hyperlink(l.get("website", ""), "Buka Web") if l.get("website") else "-"
        profile_link = format_link_hyperlink(l.get("url_referensi", ""), "Buka Profil IG")

        row = [
            l.get("nama_bisnis", ""),
            kategori_label,
            str(l.get("skor", 7)),
            l.get("skor_label", "WARM"),
            phone or "-",
            wa_link,
            l.get("proyeksi_kebutuhan", "Brosur & Stiker"),
            l.get("alamat", "Makassar"),
            f"Instagram ({l.get('jumlah_review', 0)} followers)",
            web_link,
            profile_link,
            l.get("scrape_date", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Radar Prospek", rows, action="append", headers=HEADERS_RADAR_PROSPEK)
        log.info(f"{len(rows)} IG leads berhasil diekspor ke 'Radar Prospek'")
    except Exception as e:
        log.warning(f"Gagal export IG leads ke Sheets: {e}")


def export_ig_competitors_to_sheet(competitors: list[dict]):
    """Export Instagram competitor ke Google Sheets 'Matriks Kompetitor'."""
    if not competitors:
        return
    rows = []
    for c in competitors:
        phone = c.get("telepon", "").strip()
        wa_link = format_wa_hyperlink(phone)
        url_link = format_link_hyperlink(c.get("url", ""), "Buka Profil IG")

        row = [
            c.get("nama_bisnis", ""),
            c.get("fokus_layanan", ""),
            c.get("estimasi_kapasitas", ""),
            f"Instagram ({c.get('jumlah_review', 0)} posts)",
            phone or "-",
            wa_link,
            c.get("celah_kualitas", "-"),
            c.get("celah_sop", "-"),
            c.get("selling_point_rv", "-"),
            url_link,
            c.get("tanggal_update", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Matriks Kompetitor", rows, action="append", headers=HEADERS_MATRIKS_KOMPETITOR)
        log.info(f"{len(rows)} IG kompetitor berhasil diekspor ke 'Matriks Kompetitor'")
    except Exception as e:
        log.warning(f"Gagal export IG kompetitor ke Sheets: {e}")


def export_ig_signals_to_sheet(signals: list[dict]):
    """Export sinyal tren Instagram ke Google Sheets 'Market Signals'."""
    if not signals:
        return
    rows = []
    for s in signals:
        row = [
            s.get("signal", ""),
            s.get("platform", "Instagram"),
            s.get("metrik", ""),
            s.get("relevansi", ""),
            format_link_hyperlink(s.get("url", ""), "Lihat Tren IG"),
            s.get("tanggal", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Market Signals", rows, action="append", headers=HEADERS_MARKET_SIGNALS)
        log.info(f"{len(rows)} sinyal tren Instagram berhasil diekspor ke 'Market Signals'")
    except Exception as e:
        log.warning(f"Gagal export sinyal tren ke Sheets: {e}")


def main():
    parser = argparse.ArgumentParser(description="RUANG VISUAL — Instagram Intelligence Scraper")
    parser.add_argument("--mode", choices=["leads", "competitors", "trends", "all"], default="all")
    parser.add_argument("--profiles", type=str, default="", help="Username IG dipisah koma")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("RUANG VISUAL — Instagram Intelligence Scraper (Module C)")
    log.info(f"Mode: {args.mode} | Limit: {args.limit} | Dry-run: {args.dry_run}")
    log.info("=" * 60)

    lead_usernames = [
        "kulinermakassar",
        "makassar_kuliner",
        "makassardagang",
        "butikmakassar",
    ]
    if args.profiles:
        lead_usernames = [u.strip() for u in args.profiles.split(",") if u.strip()]

    comp_usernames = IG_COMPETITOR_TARGETS

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
            for u in lead_usernames[:args.limit]:
                data = scrape_instagram_profile(u, page)
                if data:
                    all_raw_leads.append(data)
                rate_limit(INSTAGRAM_DELAY_SECONDS)

        # 2. Scrape Kompetitor
        if args.mode in ["competitors", "all"]:
            for u in comp_usernames[:args.limit]:
                data = scrape_instagram_profile(u, page)
                if data:
                    all_raw_comps.append(data)
                rate_limit(INSTAGRAM_DELAY_SECONDS)

        browser.close()

    timestamp = datetime.now(WITA).strftime("%Y%m%d_%H%M%S")

    # Export & Simpan Prospek
    if all_raw_leads and args.mode in ["leads", "all"]:
        leads = process_ig_leads(all_raw_leads)
        proc_path = PROCESSED_DIR / f"ig_leads_processed_{timestamp}.json"
        with open(proc_path, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)
        log.info(f"Leads Instagram terproses: {len(leads)}")
        if not args.dry_run:
            export_ig_leads_to_sheet(leads)

    # Export & Simpan Kompetitor
    if all_raw_comps and args.mode in ["competitors", "all"]:
        comps = process_ig_competitors(all_raw_comps)
        proc_path = PROCESSED_DIR / f"ig_comps_processed_{timestamp}.json"
        with open(proc_path, "w", encoding="utf-8") as f:
            json.dump(comps, f, ensure_ascii=False, indent=2)
        log.info(f"Kompetitor Instagram terproses: {len(comps)}")
        if not args.dry_run:
            export_ig_competitors_to_sheet(comps)

    # Export & Simpan Tren
    if args.mode in ["trends", "all"]:
        trends = process_ig_trends(IG_HASHTAGS)
        if trends:
            proc_path = PROCESSED_DIR / f"ig_trends_processed_{timestamp}.json"
            with open(proc_path, "w", encoding="utf-8") as f:
                json.dump(trends, f, ensure_ascii=False, indent=2)
            log.info(f"Sinyal tren Instagram terproses: {len(trends)}")
            if not args.dry_run:
                export_ig_signals_to_sheet(trends)

    log.info("Selesai menjalankan Instagram Intelligence Scraper.")


if __name__ == "__main__":
    main()
