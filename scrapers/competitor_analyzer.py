"""
RUANG VISUAL - Competitor Matrix & Intelligence Analyzer (Module F)
====================================================================
Modul analisis kompetitor percetakan dengan ekstraksi review negatif (1-3 bintang)
dari Google Maps untuk dijadikan selling point RUANG VISUAL.
Menganalisis kompetitor percetakan di Makassar untuk memetakan:
- Celah kualitas (Quality gaps)
- Celah SOP/Admin & pelayanan (Service gaps)
- Estimasi skala kapasitas
- Selling points diferensiasi untuk RUANG VISUAL

Referensi: intelligence_pipeline_prd.md Section 11 & 12 Sheet 2
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
from typing import List, Dict, Any, Tuple
from patchright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from scrapers.utils import get_logger, rate_limit, now_wita, today_wita, save_raw_json, launch_stealth_browser, append_rows_to_sheet
from scrapers.config import GMAPS_DELAY_SECONDS, QUALITY_KEYWORDS, SOP_KEYWORDS

logger = get_logger("competitor-analyzer")

# ─── HEADERS UNTUK GOOGLE SHEETS ─────────────────────────────────────────────
HEADERS_MATRIKS_KOMPETITOR = [
    "Nama Percetakan",
    "Fokus Layanan Utama",
    "Kapasitas / Skala",
    "Rating & Ulasan",
    "No. WhatsApp",
    "Link WA",
    "Celah Kualitas",
    "Celah Pelayanan & SOP",
    "Selling Point RUANG VISUAL",
    "Website / Maps",
    "Tanggal Update"
]


# ─── 1. COMPLAINT KEYWORDS & CLASSIFICATION ───────────────────────────────────
QUALITY_GAP_KEYWORDS = [
    'warna', 'luntur', 'pudar', 'sablon', 'cetak', 'hasil', 'kualitas',
    'buram', 'pecah', 'rusak', 'potong', 'miring', 'tidak rapi', 'jelek',
    'buruk', 'mengecewakan', 'finishing', 'jahitan', 'sobek', 'cacat',
    'tinta', 'toner', 'bercak', 'noda', 'kotor', 'tidak presisi'
]

SERVICE_GAP_KEYWORDS = [
    'lambat', 'lama', 'telat', 'terlambat', 'menunggu', 'deadline',
    'admin', 'respon', 'membalas', 'pesan', 'chat', 'komunikasi',
    'pelayanan', 'kurang ramah', 'tidak sopan', 'mengabaikan',
    'janji', 'tidak sesuai', 'estimasi', 'waktu', 'revisi', 'komplain',
    'susah dihubungi', 'tidak responsif', 'mengecewakan', 'tidak profesional'
]


def classify_complaint(review_text: str) -> Dict[str, Any]:
    """
    Klasifikasi teks keluhan ke dalam kategori Quality Gap atau Service Gap.
    
    Args:
        review_text: Teks review pelanggan
    
    Returns:
        Dictionary dengan kategori dan keyword yang terdeteksi
    """
    text_lower = review_text.lower()
    
    quality_matches = [kw for kw in QUALITY_GAP_KEYWORDS if kw in text_lower]
    service_matches = [kw for kw in SERVICE_GAP_KEYWORDS if kw in text_lower]
    
    if quality_matches and service_matches:
        category = 'both'
    elif quality_matches:
        category = 'quality_gap'
    elif service_matches:
        category = 'service_gap'
    else:
        category = 'general'
    
    return {
        'category': category,
        'quality_keywords': quality_matches,
        'service_keywords': service_matches
    }


# ─── 2. SELLING POINT GENERATOR ───────────────────────────────────────────────
SELLING_POINT_RULES = {
    'lambat': "Garansi selesai tepat waktu atau gratis biaya antar",
    'telat': "Garansi selesai tepat waktu atau gratis biaya antar",
    'lama': "Sistem produksi terstandar dengan estimasi waktu transparan",
    'deadline': "Garansi ketepatan deadline atau diskon progresif",
    
    'warna': "Menggunakan tinta pigment premium dengan garansi warna tahan cuci 100x",
    'luntur': "Garansi cetak ulang gratis jika warna luntur dalam 6 bulan",
    'pudar': "Tinta premium anti-pudar dengan teknologi heat-set terbaru",
    'sablon': "Sablon menggunakan tinta premium dengan garansi kualitas",
    
    'admin': "Admin responsif dengan SLA balasan maksimal 15 menit di jam operasional",
    'respon': "Tim CS terlatih dengan respon cepat dan tracking order real-time",
    'membalas': "WhatsApp auto-reply dan CS standby 08:00-20:00 WITA",
    'komunikasi': "Sistem komunikasi transparan dengan update progres berkala",
    
    'hasil': "Quality control 3 tahap: Pre-press, Production, dan Final Inspection",
    'kualitas': "Standar kualitas ISO dengan jaminan hasil sempurna atau cetak ulang gratis",
    'rusak': "Garansi 100% uang kembali untuk produk cacat produksi",
    'potong': "Mesin cutting digital presisi 0.1mm dengan operator bersertifikat",
    'tidak rapi': "Finishing manual oleh craftsman berpengalaman 10+ tahun",
    
    'tidak sesuai': "Approval design digital sebelum produksi dan sample fisik gratis",
    'revisi': "Revisi design unlimited hingga 100% sesuai keinginan",
    'janji': "Komitmen tertulis dalam nota dengan sanksi jelas jika tidak terpenuhi"
}


def generate_selling_point(complaint_text: str, classification: Dict[str, Any]) -> str:
    """
    Generate selling point RUANG VISUAL berdasarkan keluhan kompetitor.
    
    Args:
        complaint_text: Teks keluhan asli
        classification: Hasil klasifikasi dari classify_complaint()
    
    Returns:
        Narasi selling point yang relevan
    """
    text_lower = complaint_text.lower()
    selling_points = []
    
    # Cari keyword yang cocok dan ambil selling point-nya
    for keyword, selling_point in SELLING_POINT_RULES.items():
        if keyword in text_lower:
            if selling_point not in selling_points:
                selling_points.append(selling_point)
    
    # Jika tidak ada match spesifik, beri default berdasarkan kategori
    if not selling_points:
        if classification['category'] == 'quality_gap':
            selling_points.append("Standar kualitas ketat dengan jaminan cetak ulang gratis untuk hasil tidak memuaskan")
        elif classification['category'] == 'service_gap':
            selling_points.append("Pelayanan profesional dengan SOP terstandar dan tim CS responsif")
        else:
            selling_points.append("Komitmen kualitas dan ketepatan waktu dengan garansi kepuasan pelanggan")
    
    return " | ".join(selling_points[:2])  # Maksimal 2 selling points


# ─── 3. GMAPS REVIEW SCRAPER ──────────────────────────────────────────────────
def scrape_competitor_reviews(gmaps_url: str, max_reviews: int = 10) -> List[Dict[str, Any]]:
    """
    Scrape review negatif (1-3 bintang) dari profil Google Maps kompetitor.
    
    Args:
        gmaps_url: URL profil Google Maps kompetitor
        max_reviews: Maksimal jumlah review yang diambil
    
    Returns:
        List of review dictionaries dengan rating, text, dan klasifikasi
    """
    logger.info(f"Scraping reviews from: {gmaps_url}")
    reviews = []
    
    try:
        with sync_playwright() as p:
            browser = launch_stealth_browser(p, headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 1024},
                ignore_https_errors=True
            )
            page = context.new_page()
            
            try:
                page.goto(gmaps_url, timeout=20000, wait_until="domcontentloaded")
                rate_limit((2, 3))
                
                # Klik tab Reviews jika ada
                try:
                    reviews_button = page.locator('button:has-text("Reviews"), button:has-text("Ulasan")')
                    if reviews_button.count() > 0:
                        reviews_button.first.click()
                        rate_limit((1, 2))
                        logger.info("Clicked Reviews tab")
                except Exception:
                    logger.info("Reviews tab not found or already active")
                
                # Tunggu review cards muncul
                page.wait_for_selector('div[data-review-id], div.jftiEf', timeout=10000)
                rate_limit((1, 2))
                
                # Coba klik filter "Sort" untuk mengurutkan dari rating terendah
                try:
                    sort_button = page.locator('button:has-text("Sort"), button:has-text("Urutkan")')
                    if sort_button.count() > 0:
                        sort_button.first.click()
                        rate_limit((0.5, 1))
                        
                        # Pilih "Lowest rating" / "Rating terendah"
                        lowest_option = page.locator('div[role="menuitemradio"]:has-text("Lowest"), div[role="menuitemradio"]:has-text("Terendah")')
                        if lowest_option.count() > 0:
                            lowest_option.first.click()
                            rate_limit((1, 2))
                            logger.info("Sorted by lowest rating")
                except Exception as e:
                    logger.info(f"Could not apply sort filter: {e}")
                
                # Scroll review feed untuk load lebih banyak
                scrollable_div = page.locator('div.m6QErb.DxyBCb.kA9KIf.dS8AEf').first
                for _ in range(3):
                    try:
                        scrollable_div.evaluate('el => el.scrollTo(0, el.scrollHeight)')
                        rate_limit((1, 2))
                    except Exception:
                        break
                
                # Ekstrak review cards
                review_cards = page.locator('div.jftiEf').all()
                logger.info(f"Found {len(review_cards)} review cards")
                
                for card in review_cards[:max_reviews]:
                    try:
                        # Ekstrak rating (jumlah bintang terisi)
                        star_elements = card.locator('span.kvMYJc').get_attribute('aria-label')
                        rating_match = re.search(r'(\d+)', star_elements) if star_elements else None
                        rating = int(rating_match.group(1)) if rating_match else 0
                        
                        # Filter hanya rating 1-3
                        if rating > 3:
                            continue
                        
                        # Ekspand "More" button jika ada
                        try:
                            more_button = card.locator('button.w8nwRe.kyuRq')
                            if more_button.count() > 0:
                                more_button.click()
                                rate_limit((0.3, 0.5))
                        except Exception:
                            pass
                        
                        # Ekstrak teks review
                        review_text_elem = card.locator('span.wiI7pd')
                        review_text = review_text_elem.inner_text() if review_text_elem.count() > 0 else ""
                        
                        if not review_text or len(review_text.strip()) < 10:
                            continue
                        
                        # Klasifikasi keluhan
                        classification = classify_complaint(review_text)
                        
                        # Generate selling point
                        selling_point = generate_selling_point(review_text, classification)
                        
                        reviews.append({
                            'rating': rating,
                            'text': review_text.strip(),
                            'classification': classification['category'],
                            'quality_keywords': classification['quality_keywords'],
                            'service_keywords': classification['service_keywords'],
                            'selling_point_rv': selling_point,
                            'scraped_at': now_wita()
                        })
                        
                        logger.info(f"Extracted {rating}-star review: {review_text[:60]}...")
                        
                    except Exception as e:
                        logger.warning(f"Error extracting review card: {e}")
                        continue
                
                logger.info(f"Successfully extracted {len(reviews)} negative reviews")
                
            except PlaywrightTimeout:
                logger.error(f"Timeout loading {gmaps_url}")
            except Exception as e:
                logger.error(f"Error during scraping: {e}")
            finally:
                context.close()
                browser.close()
                
    except Exception as e:
        logger.error(f"Browser initialization error: {e}")
    
    return reviews


# ─── 4. LEGACY ANALYSIS FUNCTIONS FOR PIPELINE COMPATIBILITY ─────────────────
def analyze_single_competitor(comp: dict) -> dict:
    """
    Analisis satu kompetitor berdasarkan data metrik, kontak, dan ulasan.
    Mendukung integrasi dengan review mining baru.
    """
    nama = comp.get("nama_bisnis", "Unknown")
    rating = float(comp.get("rating", 0.0))
    reviews = int(comp.get("jumlah_review", 0))
    phone = comp.get("telepon", "")
    web = comp.get("website", "")
    alamat = comp.get("alamat", "")

    # 1. Estimasi Kapasitas & Skala Operasional
    if reviews >= 500:
        kapasitas = f"Skala Besar ({reviews} ulasan, volume tinggi)"
    elif reviews >= 100:
        kapasitas = f"Skala Menengah ({reviews} ulasan, volume moderat)"
    elif reviews >= 20:
        kapasitas = f"Skala Berkembang ({reviews} ulasan)"
    else:
        kapasitas = f"Skala Kecil / Baru ({reviews} ulasan)"

    # 2. Fokus Layanan Utama (Inferred dari nama & spesialisasi)
    nama_lower = nama.lower()
    if "digital" in nama_lower:
        layanan = "Digital Printing, Banner, Sticker, Cetak Cepat"
    elif "offset" in nama_lower:
        layanan = "Percetakan Offset, Brosur Massal, Kemasan Box"
    elif "toko" in nama_lower or "store" in nama_lower:
        layanan = "Retail Printing, Fotokopi, Jilid, Alat Tulis"
    elif "sablon" in nama_lower or "konveksi" in nama_lower:
        layanan = "Sablon Kaos, Merchandise, Spanduk Kain"
    else:
        layanan = "Percetakan Umum, Banner, Kartu Nama, Brosur"

    # 3. Analisis Celah Kualitas & Celah SOP/Admin
    # Jika kompetitor sudah punya data review mining, gunakan itu
    if comp.get('celah_kualitas_from_reviews'):
        celah_kualitas = comp.get('celah_kualitas_from_reviews', '')
        celah_sop = comp.get('celah_pelayanan_sop_from_reviews', '')
        selling_points_text = comp.get('selling_point_ruang_visual_from_reviews', '')
    else:
        # Fallback ke analisis heuristik berdasarkan rating
        celah_kualitas = []
        celah_sop = []
        selling_points = []

        if rating < 4.5 and reviews > 10:
            celah_kualitas.append(f"Rating rendah ({rating}/5.0) — risiko deviasi warna/finishing")
            celah_sop.append("Indikasi ketidakpuasan customer pada ketepatan waktu/admin")
            selling_points.append("Tawarkan garansi cetak ulang & proofing warna presisi")
        elif rating < 4.8 and reviews > 50:
            celah_kualitas.append(f"Rating {rating}/5.0 — kualitas standar, rentan saat overload")
            celah_sop.append("Potensi antrean panjang saat jam sibuk")
            selling_points.append("Tawarkan prioritas pengerjaan kilat & sistem order online")
        else:
            celah_kualitas.append("Kualitas dinilai baik oleh customer")
            celah_sop.append("Pelayanan stabil")
            selling_points.append("Menangkan dengan harga bundling merchandise & packaging kreatif")

        if not phone:
            celah_sop.append("Akses kontak WhatsApp langsung tidak ditampilkan di publik")
            selling_points.append("Kemudahan konsultasi via fast-response WhatsApp")
        else:
            celah_sop.append(f"Tersedia kontak langsung ({phone})")

        celah_kualitas = "; ".join(celah_kualitas)
        celah_sop = "; ".join(celah_sop)
        selling_points_text = "; ".join(selling_points)

    return {
        "nama_bisnis": nama,
        "fokus_layanan": layanan,
        "celah_kualitas": celah_kualitas,
        "celah_sop": celah_sop,
        "estimasi_kapasitas": kapasitas,
        "estetika_visual": "Perlu audit portofolio IG",
        "rating_gmaps": str(rating),
        "jumlah_review": str(reviews),
        "telepon": phone,
        "website": web,
        "alamat": alamat,
        "selling_point_rv": selling_points_text,
        "tanggal_update": today_wita(),
    }


def analyze_all_competitors(competitors: list[dict]) -> list[dict]:
    """
    Analisis seluruh daftar kompetitor dan urutkan berdasarkan urgensi persaingan.
    Mendukung integrasi dengan review mining otomatis.
    """
    matrix = []
    
    for comp in competitors:
        # Jika kompetitor memiliki gmaps_url, coba scrape review negatif
        gmaps_url = comp.get('url_gmaps', '') or comp.get('link_maps', '')
        
        if gmaps_url and gmaps_url not in ['-', '', 'None']:
            logger.info(f"Mining reviews for: {comp.get('nama_bisnis', 'Unknown')}")
            try:
                reviews = scrape_competitor_reviews(gmaps_url, max_reviews=5)
                
                if reviews:
                    # Aggregate insights from reviews
                    quality_gaps = []
                    service_gaps = []
                    all_selling_points = []
                    
                    for review in reviews:
                        if review['classification'] in ['quality_gap', 'both']:
                            quality_gaps.append(review['text'][:100])
                        if review['classification'] in ['service_gap', 'both']:
                            service_gaps.append(review['text'][:100])
                        all_selling_points.append(review['selling_point_rv'])
                    
                    # Inject review mining results into competitor data
                    comp['celah_kualitas_from_reviews'] = ' | '.join(quality_gaps[:2]) if quality_gaps else ''
                    comp['celah_pelayanan_sop_from_reviews'] = ' | '.join(service_gaps[:2]) if service_gaps else ''
                    comp['selling_point_ruang_visual_from_reviews'] = ' / '.join(list(dict.fromkeys(all_selling_points))[:2]) if all_selling_points else ''
                    
            except Exception as e:
                logger.warning(f"Could not mine reviews for {comp.get('nama_bisnis')}: {e}")
        
        # Analyze with or without review mining data
        analyzed = analyze_single_competitor(comp)
        matrix.append(analyzed)
    
    # Sort by review count (market share)
    matrix.sort(key=lambda x: int(x["jumlah_review"]), reverse=True)
    return matrix


# ─── 5. GOOGLE SHEETS EXPORT FUNCTIONS ───────────────────────────────────────
def format_wa_hyperlink(phone: str) -> str:
    """Format nomor telepon menjadi hyperlink WhatsApp untuk Google Sheets."""
    if not phone:
        return "-"
    clean = "".join([c for c in phone if c.isdigit()])
    if clean.startswith("08"):
        clean = "62" + clean[1:]
    elif clean.startswith("8"):
        clean = "62" + clean
    return f'=HYPERLINK("https://wa.me/{clean}", "Chat WA")' if clean else "-"


def format_link_hyperlink(url: str, label: str = "Buka Web") -> str:
    """Format URL menjadi hyperlink untuk Google Sheets."""
    if not url or url == "-":
        return "-"
    return f'=HYPERLINK("{url}", "{label}")'


def export_matrix_to_sheet(matrix: list[dict], action: str = "append"):
    """
    Export Matriks Kompetitor lengkap ke Google Sheets.
    
    Args:
        matrix: List of analyzed competitor dictionaries
        action: 'append' or 'replace' sheet data
    """
    rows = []
    for m in matrix:
        phone = m.get("telepon", "").strip()
        wa_link = format_wa_hyperlink(phone)
        web_or_map = m.get("website", "") or m.get("url_gmaps", "")
        web_link = format_link_hyperlink(web_or_map, "Buka Web") if web_or_map else "-"
        rating_str = f"{m.get('rating_gmaps', '0.0')} ({m.get('jumlah_review', '0')} ulasan)"

        row = [
            m.get("nama_bisnis", ""),              # A: Nama Percetakan
            m.get("fokus_layanan", ""),            # B: Fokus Layanan Utama
            m.get("estimasi_kapasitas", ""),       # C: Kapasitas / Skala
            rating_str,                            # D: Rating & Ulasan
            phone or "-",                          # E: No. WhatsApp
            wa_link,                               # F: Link WA
            m.get("celah_kualitas", "-"),          # G: Celah Kualitas
            m.get("celah_sop", "-"),               # H: Celah Pelayanan & SOP
            m.get("selling_point_rv", "-"),        # I: Selling Point RUANG VISUAL
            web_link,                              # J: Website / Maps
            m.get("tanggal_update", today_wita()), # K: Tanggal Update
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Matriks Kompetitor", rows, action=action, headers=HEADERS_MATRIKS_KOMPETITOR)
        logger.info(f"{len(rows)} baris berhasil di-export ke 'Matriks Kompetitor'")
    except Exception as e:
        logger.warning(f"Belum bisa export ke Google Sheets: {e}")
        logger.info("Matriks kompetitor tetap tersimpan di folder data/processed/")


# ─── 7. CLI INTERFACE ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="RUANG VISUAL Competitor Analyzer - Mine negative reviews for selling points"
    )
    parser.add_argument(
        '--url',
        type=str,
        help='Single Google Maps URL to test scraping'
    )
    parser.add_argument(
        '--input',
        type=str,
        help='JSON file with competitor list (must have gmaps_url field)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=5,
        help='Maximum competitors to analyze (default: 5)'
    )
    parser.add_argument(
        '--max-reviews',
        type=int,
        default=10,
        help='Maximum reviews per competitor (default: 10)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test mode: scrape but do not save results'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output JSON file path (optional, auto-generated if not provided)'
    )
    
    args = parser.parse_args()
    
    # Mode 1: Test single URL
    if args.url:
        logger.info(f"Testing single competitor URL: {args.url}")
        reviews = scrape_competitor_reviews(args.url, max_reviews=args.max_reviews)
        
        print(f"\n--- Found {len(reviews)} Negative Reviews ---")
        for i, review in enumerate(reviews, 1):
            print(f"\n{i}. Rating: {review['rating']} stars")
            print(f"   Category: {review['classification']}")
            print(f"   Review: {review['text'][:100]}...")
            print(f"   Selling Point RV: {review['selling_point_rv']}")
        
        return
    
    # Mode 2: Batch processing from JSON
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"Input file not found: {args.input}")
            return
        
        with open(input_path, 'r', encoding='utf-8') as f:
            competitors = json.load(f)
        
        logger.info(f"Loaded {len(competitors)} competitors from {args.input}")
        
        # Limit batch size
        competitors_to_analyze = competitors[:args.limit]
        
        results = analyze_competitors(competitors_to_analyze, max_reviews_per_competitor=args.max_reviews)
        
        logger.info(f"Analysis complete: {len(results)} competitors analyzed")
        
        if not args.dry_run:
            if args.output:
                output_path = Path(args.output)
            else:
                output_path = save_raw_json(results, 'competitor_analysis')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Results saved to: {output_path}")
        else:
            logger.info("Dry run mode: results not saved")
        
        return
    
    # No mode selected
    logger.error("Please specify --url for single test or --input for batch processing")
    parser.print_help()


if __name__ == "__main__":
    main()
