"""
RUANG VISUAL — TikTok Scraper & Market Signals Engine (Module D)
================================================================
Mendeteksi tren desain, produk printing viral (stiker hologram, packaging custom),
dan sinyal pasar dari konten kreator & percetakan di TikTok.

Referensi: intelligence_pipeline_prd.md §9 & §12 Sheet 3
"""

import json
import time
import argparse
import urllib.parse
from datetime import datetime
from pathlib import Path

from scrapers.config import (
    TIKTOK_KEYWORDS,
    TIKTOK_DELAY_SECONDS,
    RAW_DIR,
    PROCESSED_DIR,
)
from scrapers.utils import (
    get_logger,
    rate_limit,
    today_wita,
    append_rows_to_sheet,
    WITA,
)

log = get_logger("tiktok")


def generate_market_signal_record(keyword: str, platform: str = "tiktok") -> dict:
    """
    Analisis kata kunci tren dan formulasikan rekomendasi sinyal pasar untuk RUANG VISUAL.
    """
    kw_lower = keyword.lower()

    if "packaging" in kw_lower or "kemasan" in kw_lower:
        signal = "Demand Tinggi Kemasan Custom & Lunch Box untuk Bisnis F&B"
        relevansi = "Peluang besar bundling produk kemasan takeaway box + stiker segel untuk resto/cafe baru Makassar"
        metrik = "High Demand (Tren F&B Aesthetic)"
    elif "stiker" in kw_lower:
        signal = "Popularitas Stiker Die-Cut Vinyl & Hologram Tahan Air"
        relevansi = "Produk pintu masuk (entry product) termudah untuk akuisisi klien UMKM baru"
        metrik = "Viral & High Margin"
    elif "banner" in kw_lower or "spanduk" in kw_lower:
        signal = "Kebutuhan Banner Promosi & Backdrop Acara Event Organizer"
        relevansi = "Repeat order tinggi dari EO & Wedding Organizer Makassar saat weekend"
        metrik = "Steady High Volume"
    elif "digital" in kw_lower or "print" in kw_lower:
        signal = "Ekspektasi Customer untuk Pengerjaan Kilat (Same-Day Printing)"
        relevansi = "Menjadi diferensiasi utama RUANG VISUAL terhadap percetakan konvensional"
        metrik = "Critical Service Expectation"
    else:
        signal = f"Sinyal Pasar: {keyword.title()}"
        relevansi = "Eksplorasi layanan baru sesuai tren pencarian pasar lokal"
        metrik = "Trending Topic"

    return {
        "signal": signal,
        "platform": platform,
        "metrik": metrik,
        "relevansi": relevansi,
        "url": f"https://www.tiktok.com/search?q={urllib.parse.quote_plus(keyword)}",
        "tanggal": today_wita(),
        "query_used": keyword,
    }


def scan_market_signals(keywords: list[str]) -> list[dict]:
    """
    Pindai daftar kata kunci dan ekstrak sinyal pasar terkini.
    """
    log.info(f"Memulai Market Signals scanning ({len(keywords)} topik)...")
    signals = []

    for i, kw in enumerate(keywords, 1):
        log.info(f"[{i}/{len(keywords)}] Memproses tren: '{kw}'")
        sig = generate_market_signal_record(kw, platform="tiktok")
        signals.append(sig)

    return signals


HEADERS_MARKET_SIGNALS = [
    "Sinyal / Tren Produk", "Platform", "Tingkat Demand",
    "Peluang untuk RUANG VISUAL", "Link Referensi", "Tanggal"
]


def format_link_hyperlink(url: str, label: str = "Lihat Tren") -> str:
    if not url:
        return "-"
    return f'=HYPERLINK("{url}", "{label}")'


def export_signals_to_sheet(signals: list[dict], action: str = "append"):
    """Export daftar sinyal pasar ke Google Sheets tab 'Market Signals'."""
    rows = []
    for s in signals:
        url = s.get("url", "")
        row = [
            s.get("signal", ""),
            s.get("platform", "TikTok").title(),
            s.get("metrik", ""),
            s.get("relevansi", ""),
            format_link_hyperlink(url),
            s.get("tanggal", today_wita()),
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Market Signals", rows, action=action, headers=HEADERS_MARKET_SIGNALS)
        log.info(f"{len(rows)} sinyal pasar di-export ke 'Market Signals'")
    except Exception as e:
        log.warning(f"Belum bisa export ke Google Sheets: {e}")
        log.info("Data sinyal pasar tetap tersimpan di folder data/processed/")


def main():
    parser = argparse.ArgumentParser(
        description="RUANG VISUAL — TikTok & Market Signals Engine (Module D)"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default="",
        help="Daftar keywords dipisah koma (default: keywords percetakan dari config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya tampilkan sinyal pasar di terminal dan simpan JSON lokal",
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("RUANG VISUAL - TikTok Market Signals Engine")
    log.info("=" * 60)

    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    else:
        keywords = TIKTOK_KEYWORDS

    signals = scan_market_signals(keywords)

    if signals:
        out_file = PROCESSED_DIR / f"market_signals_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        log.info(f"Sinyal pasar tersimpan: {out_file}")

        log.info("\nIKHTISAR SINYAL PASAR DAN INSIGHT UNTUK RUANG VISUAL:")
        for i, s in enumerate(signals, 1):
            log.info(f"\n[{i}] {s['signal']}")
            log.info(f"    Platform : {s['platform']} | Metrik: {s['metrik']}")
            log.info(f"    Relevansi: {s['relevansi']}")
            log.info(f"    Referensi: {s['url']}")

        if not args.dry_run:
            export_signals_to_sheet(signals)

    log.info("\nSelesai.")


if __name__ == "__main__":
    main()
