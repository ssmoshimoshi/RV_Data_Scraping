"""
RUANG VISUAL — Instagram Scraper (Module C)
============================================
Scrape data profil publik Instagram untuk lead discovery & competitor monitoring.
Referensi: intelligence_pipeline_prd.md §8

Fitur:
    - Stealth headless browser via Patchright (tanpa login, data publik)
    - Ekstraksi: Username, Nama Display, Bio, Followers, Following, Post Count, Link Bio, Kontak WA
    - Kategori auto-detect & scoring via Lead Scoring Engine (Module E)
    - Rate limit ketat (max 15 profil per sesi, delay 5-8s)
    - Simpan lokal di data/raw/ & data/processed/ serta export ke Google Sheets
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
    """
    Scrape data 1 profil Instagram publik.
    """
    clean_username = username.strip().replace("@", "")
    url = f"https://www.instagram.com/{clean_username}/"
    log.info(f"📸 Scraping @{clean_username} ({url})")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)
    except Exception as e:
        log.warning(f"  Timeout loading @{clean_username}: {e}")
        return None

    # Cek apakah dialihkan ke login
    if "/accounts/login" in page.url:
        log.warning(f"  ⚠️ Redirected to login page for @{clean_username}. Instagram rate limit.")
        return None

    # 1. Ekstraksi dari Meta Tags
    og_desc = page.query_selector('meta[name="description"], meta[property="og:description"]')
    meta_text = og_desc.get_attribute("content") if og_desc else ""

    followers = 0
    following = 0
    posts = 0

    if meta_text:
        # Format: "X Followers, Y Following, Z Posts..." atau bahasa Indonesia "X Pengikut, Y Mengikuti..."
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

        # Filter out numbers & stats lines untuk dapatkan display name & bio
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

        # Ekstraksi tautan eksternal (link in bio)
        links = header.query_selector_all("a[href]")
        for a in links:
            href = a.get_attribute("href") or ""
            if "instagram.com" not in href and href.startswith("http"):
                external_link = href
                break
            elif "linktr.ee" in href or "wa.me" in href or "bit.ly" in href:
                external_link = href
                break

    # 3. Deteksi Kontak Telepon / WhatsApp dari Bio
    combined_text = f"{bio} {external_link}"
    phone_match = re.search(r"((?:\+62|08)[0-9]{1,4}[- ]?[0-9]{3,5}[- ]?[0-9]{3,5})", combined_text)
    if phone_match:
        phone = phone_match.group(1).strip()
    elif "wa.me/" in external_link:
        wa_m = re.search(r"wa\.me/([0-9]+)", external_link)
        if wa_m:
            phone = wa_m.group(1).strip()

    # Kategori bisnis
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
        "source": "instagram",
        "url_profil": f"https://www.instagram.com/{clean_username}/",
    }


def scrape_profiles(usernames: list[str], max_profiles: int = INSTAGRAM_MAX_PAGES_PER_SESSION) -> list[dict]:
    """
    Scrape kumpulan profil Instagram dengan rate limiting ketat.
    """
    results = []
    targets = usernames[:max_profiles]
    log.info(f"📸 Memulai Instagram profile scraper — {len(targets)} target")

    with sync_playwright() as p:
        browser = launch_stealth_browser(p, headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="id-ID",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        for i, username in enumerate(targets, 1):
            log.info(f"[{i}/{len(targets)}] Target: @{username}")
            data = scrape_instagram_profile(username, page)

            if data:
                results.append(data)
                log.info(f"  ✅ Followers: {data['jumlah_followers']} | WA: {data['kontak'] or '-'} | Kategori: {data['kategori_kode']}")
            else:
                log.warning(f"  ❌ Gagal mengambil data @{username}")

            if i < len(targets):
                delay = rate_limit(INSTAGRAM_DELAY_SECONDS)
                log.info(f"  ⏳ Delay anti-ban: {delay:.1f}s")

        browser.close()

    return results


def process_and_score_ig_leads(profiles: list[dict]) -> list[dict]:
    """
    Hitung skor prospek untuk leads dari Instagram.
    """
    processed = []
    for p in profiles:
        lead = {
            "nama_bisnis": p["nama_display"] or p["username"],
            "kategori": p.get("kategori_kode", "lainnya"),
            "telepon": p.get("kontak", ""),
            "website": p.get("website_link", ""),
            "instagram": f"@{p['username']}",
            "rating": 0.0,
            "is_new_3months": p.get("jumlah_followers", 0) < 500,  # Akun UMKM awal
            "is_new_6months": False,
            "lokasi_makassar_kota": "makassar" in p.get("bio", "").lower(),
        }

        scored = score_and_format(lead)
        p["skor"] = scored["skor"]
        p["skor_label"] = scored["skor_label"]
        p["skor_reasons"] = scored["skor_reasons"]
        processed.append(p)

    processed.sort(key=lambda x: x.get("skor", 0), reverse=True)
    return processed


def export_ig_leads_to_sheet(leads: list[dict]):
    """Export Instagram leads ke sheet 'Radar Prospek'."""
    rows = []
    for l in leads:
        kategori_label = {
            "fnb": "F&B",
            "eo": "Event Organizer",
            "retail": "Retail/UMKM",
            "instansi": "Instansi/Kantor",
            "percetakan": "Percetakan",
            "lainnya": "Lainnya",
        }.get(l.get("kategori_kode", ""), "Lainnya")

        kebutuhan_map = {
            "fnb": "Packaging box, stiker label, cup sleeve, menu",
            "eo": "Banner, backdrop, undangan, name tag",
            "retail": "Thank you card, stiker pengiriman, shopping bag",
            "lainnya": "Brosur, kartu nama, banner promosi",
        }
        kebutuhan = kebutuhan_map.get(l.get("kategori_kode", ""), "Brosur, kartu nama")

        row = [
            l.get("nama_display", l.get("username", "")), # A: Entitas Bisnis
            kategori_label,                                # B: Kategori Segmen
            f"Akun IG Aktif ({l.get('jumlah_followers', 0)} followers)", # C: Trigger Event
            "instagram",                                   # D: Sumber Data
            l.get("kontak", f"@{l.get('username', '')}"),  # E: Kontak
            kebutuhan,                                     # F: Proyeksi Kebutuhan
            str(l.get("skor", 1)),                         # G: Skor Prospek
            "BARU",                                        # H: Status Akuisisi
            l.get("url_profil", ""),                       # I: URL Referensi
            l.get("scrape_date", today_wita()),            # J: Tanggal Scrape
            f"{l.get('skor_label', '')} | Bio: {l.get('bio', '')[:80].replace(chr(10), ' ')}", # K: Catatan
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Radar Prospek", rows)
        log.info(f"📊 {len(rows)} IG leads di-export ke 'Radar Prospek'")
    except Exception as e:
        log.warning(f"⚠️  Belum bisa export ke Google Sheets: {e}")
        log.info("ℹ️  Data tetap aman tersimpan di folder data/processed/")


def main():
    parser = argparse.ArgumentParser(
        description="RUANG VISUAL — Instagram Scraper (Module C)"
    )
    parser.add_argument(
        "--profiles",
        type=str,
        default="",
        help="Daftar username IG dipisah koma (contoh: phinisi.printing,kulinermakassar)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=INSTAGRAM_MAX_PAGES_PER_SESSION,
        help="Limit jumlah profil yang diproses (max 15)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya scrape dan simpan JSON lokal tanpa export Sheets",
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("📸  RUANG VISUAL — Instagram Intelligence Scraper")
    log.info("=" * 60)

    # Profil default jika tidak dispesifikasikan (kombinasi kompetitor & brand kuliner Makassar)
    if args.profiles:
        usernames = [u.strip() for u in args.profiles.split(",") if u.strip()]
    else:
        # Default sample profil Makassar untuk pengujian
        usernames = [
            "ruangvisual.id",
            "kulinermakassar",
            "makassar_kuliner",
            "makassardagang",
        ]

    raw_data = scrape_profiles(usernames, max_profiles=min(args.limit, 15))

    if raw_data:
        raw_path = RAW_DIR / f"instagram_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        log.info(f"💾 Raw data disimpan: {raw_path}")

        scored_leads = process_and_score_ig_leads(raw_data)
        proc_path = PROCESSED_DIR / f"ig_leads_scored_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
        with open(proc_path, "w", encoding="utf-8") as f:
            json.dump(scored_leads, f, ensure_ascii=False, indent=2)
        log.info(f"💾 Processed & scored data disimpan: {proc_path}")

        log.info("\n📊 HASIL SCRAPING PROFIL INSTAGRAM:")
        for l in scored_leads:
            log.info(f"  → @{l['username']} ({l['nama_display']}) | Followers: {l['jumlah_followers']} | WA: {l.get('kontak') or '-'} | Skor: {l['skor']}/10 ({l['skor_label']})")

        if not args.dry_run:
            export_ig_leads_to_sheet(scored_leads)

    log.info("\n✅ Selesai!")


if __name__ == "__main__":
    main()
