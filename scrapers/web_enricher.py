"""
RUANG VISUAL - Web Enricher & Bio Link Contact Extractor
=========================================================
Modul pengayaan kontak melalui ekstraksi nomor WhatsApp dari website bisnis
atau link bio (Linktree, Beacons, Instagram bio) untuk calon pelanggan yang
belum memiliki nomor telepon di Google Maps.
Bebas emoji sesuai aturan operasional RUANG VISUAL.
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import argparse
import json
from typing import Optional, List, Dict, Any
from patchright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from scrapers.utils import get_logger, rate_limit, now_wita, save_raw_json
from scrapers.contact_enricher import classify_phone_number

logger = get_logger("web-enricher")


# ─── 1. BIO LINK AGGREGATOR DETECTION ────────────────────────────────────────
BIO_LINK_AGGREGATORS = [
    'linktr.ee',
    'beacons.ai',
    'campsite.bio',
    'heylink.me',
    'biolinky.co',
    'bio.link',
    'linkin.bio',
    'tap.bio'
]


def is_bio_link_aggregator(url: str) -> bool:
    """Check if URL is a bio link aggregator platform."""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in BIO_LINK_AGGREGATORS)


# ─── 2. REGEX PATTERNS UNTUK EKSTRAKSI WHATSAPP ──────────────────────────────
WHATSAPP_PATTERNS = [
    # Pattern 1: wa.me links (with optional slash and query params)
    r'wa\.me/\??(\+?62\d{9,13})',
    r'wa\.me/\??(\+?08\d{8,12})',
    
    # Pattern 2: api.whatsapp.com links (with optional slash before query)
    r'api\.whatsapp\.com/send/?\?phone=(\+?62\d{9,13})',
    r'api\.whatsapp\.com/send/?\?phone=(\+?08\d{8,12})',
    
    # Pattern 3: web.whatsapp.com links
    r'web\.whatsapp\.com/send\?phone=(\+?62\d{9,13})',
    r'web\.whatsapp\.com/send\?phone=(\+?08\d{8,12})',
    
    # Pattern 4: Indonesian phone numbers in text
    r'(?:whatsapp|wa|contact|hubungi|telepon|hp|handphone)[:\s]*(\+?62\s?\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{0,4})',
    r'(?:whatsapp|wa|contact|hubungi|telepon|hp|handphone)[:\s]*(0\d{2,3}[\s-]?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{0,4})',
    
    # Pattern 5: Generic Indonesian mobile numbers
    r'\+62[\s-]?8\d{2}[\s-]?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{0,4}',
    r'08\d{2}[\s-]?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{0,4}',
]


def extract_whatsapp_from_text(text: str) -> List[str]:
    """
    Ekstrak semua kemungkinan nomor WhatsApp dari teks HTML atau plain text.
    Returns list of candidate phone numbers.
    """
    candidates = []
    text_lower = text.lower()
    
    for pattern in WHATSAPP_PATTERNS:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            if match.groups():
                phone = match.group(1)
            else:
                phone = match.group(0)
            
            # Clean up extracted number
            phone_cleaned = re.sub(r'[^\d+]', '', phone)
            if phone_cleaned and len(phone_cleaned) >= 10:
                candidates.append(phone_cleaned)
    
    return candidates


def validate_and_select_best_number(candidates: List[str]) -> Optional[str]:
    """
    Validasi kandidat nomor dan pilih yang paling valid.
    Prioritas: nomor dengan format 62 > format 08 > lainnya.
    """
    if not candidates:
        return None
    
    valid_numbers = []
    for num in candidates:
        # Validate with contact_enricher
        phone_info = classify_phone_number(num)
        if phone_info['type'] == 'whatsapp' and phone_info['is_wa_ready']:
            valid_numbers.append(phone_info['clean_number'])
    
    if not valid_numbers:
        return None
    
    # Return first valid number (deduped)
    return valid_numbers[0]


# ─── 3. WEB SCRAPING DENGAN PLAYWRIGHT STEALTH ───────────────────────────────
def scrape_website_for_whatsapp(url: str, timeout: int = 15000) -> Optional[str]:
    """
    Buka website target dan ekstrak nomor WhatsApp dari:
    1. Link href wa.me atau api.whatsapp.com
    2. Text content di footer, contact section, atau body
    3. Bio link aggregators (Linktree, Beacons, etc) - extract outbound WA links
    
    Returns: Clean WhatsApp number in format 628xxx or None
    """
    if not url or url in ["-", "", "None"]:
        return None
    
    # Ensure URL has protocol
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Check if this is a bio link aggregator
    is_aggregator = is_bio_link_aggregator(url)
    if is_aggregator:
        logger.info(f"Detected bio link aggregator: {url}")
    else:
        logger.info(f"Scraping: {url}")
    
    try:
        with sync_playwright() as p:
            from scrapers.utils import launch_stealth_browser
            browser = launch_stealth_browser(p, headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            page = context.new_page()
            
            try:
                page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                rate_limit((1, 2))
                
                # For bio link aggregators, prioritize outbound WhatsApp links
                if is_aggregator:
                    logger.info("Extracting WhatsApp links from bio aggregator")
                    try:
                        # Extract all link hrefs
                        all_links = page.eval_on_selector_all('a[href]', 'elements => elements.map(e => e.href)')
                        
                        # Filter for WhatsApp links
                        wa_links = [link for link in all_links if 
                                   'wa.me' in link.lower() or 
                                   'whatsapp.com' in link.lower() or
                                   'api.whatsapp' in link.lower()]
                        
                        if wa_links:
                            logger.info(f"Found {len(wa_links)} WhatsApp link(s) in aggregator")
                            # Extract phone numbers from these links
                            candidates = []
                            for wa_link in wa_links:
                                extracted = extract_whatsapp_from_text(wa_link)
                                candidates.extend(extracted)
                            
                            if candidates:
                                best_number = validate_and_select_best_number(candidates)
                                if best_number:
                                    logger.info(f"Found WhatsApp from aggregator: {best_number}")
                                    return best_number
                    except Exception as e:
                        logger.warning(f"Error extracting from aggregator: {e}")
                
                # Standard extraction for all sites (including aggregator fallback)
                # Extract all text content
                body_text = page.inner_text('body')
                
                # Extract all href attributes
                all_links = page.eval_on_selector_all('a[href]', 'elements => elements.map(e => e.href)')
                links_text = ' '.join(all_links)
                
                # Combine for extraction
                full_content = f"{body_text} {links_text}"
                
                # Extract candidates
                candidates = extract_whatsapp_from_text(full_content)
                
                # Validate and select best
                best_number = validate_and_select_best_number(candidates)
                
                if best_number:
                    logger.info(f"Found WhatsApp: {best_number}")
                else:
                    logger.info("No valid WhatsApp number found")
                
                return best_number
                
            except PlaywrightTimeout:
                logger.warning(f"Timeout loading {url}")
                return None
            except Exception as e:
                logger.warning(f"Error scraping {url}: {e}")
                return None
            finally:
                context.close()
                browser.close()
                
    except Exception as e:
        logger.error(f"Browser initialization error: {e}")
        return None


# ─── 3. BATCH PROCESSING WITH SHARED BROWSER ─────────────────────────────────
def enrich_leads_from_websites(leads: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Process batch of leads and enrich missing phone numbers from their websites.
    Uses shared browser context for efficiency.
    
    Args:
        leads: List of lead dictionaries with 'website' and 'telepon' fields
        limit: Maximum number of websites to scrape
    
    Returns:
        List of enriched leads with updated phone numbers
    """
    enriched = []
    scraped_count = 0
    
    # Prepare list of leads that need enrichment
    leads_to_scrape = []
    for lead in leads:
        existing_phone = lead.get('telepon', '') or lead.get('no_whatsapp', '')
        phone_info = classify_phone_number(existing_phone)
        
        if phone_info['is_wa_ready']:
            logger.info(f"Skip {lead.get('nama_bisnis', 'Unknown')}: already has WhatsApp")
            enriched.append(lead)
            continue
        
        website = lead.get('website', '') or lead.get('link_bio', '')
        if not website or website in ['-', '', 'None']:
            logger.info(f"Skip {lead.get('nama_bisnis', 'Unknown')}: no website")
            enriched.append(lead)
            continue
        
        if scraped_count < limit:
            leads_to_scrape.append((lead, website))
            scraped_count += 1
        else:
            enriched.append(lead)
    
    if not leads_to_scrape:
        logger.info("No leads require enrichment")
        return enriched
    
    # Shared browser session for batch scraping
    logger.info(f"Starting batch enrichment for {len(leads_to_scrape)} leads")
    try:
        with sync_playwright() as p:
            from scrapers.utils import launch_stealth_browser
            browser = launch_stealth_browser(p, headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            
            for lead, website in leads_to_scrape:
                url = website if website.startswith(('http://', 'https://')) else 'https://' + website
                logger.info(f"Scraping: {url}")
                
                try:
                    page = context.new_page()
                    page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    rate_limit((1, 2))
                    
                    # Extract content
                    body_text = page.inner_text('body')
                    all_links = page.eval_on_selector_all('a[href]', 'elements => elements.map(e => e.href)')
                    links_text = ' '.join(all_links)
                    full_content = f"{body_text} {links_text}"
                    
                    # Extract and validate
                    candidates = extract_whatsapp_from_text(full_content)
                    whatsapp_number = validate_and_select_best_number(candidates)
                    
                    if whatsapp_number:
                        phone_info = classify_phone_number(whatsapp_number)
                        lead['telepon'] = phone_info['formatted']
                        lead['no_whatsapp'] = phone_info['clean_number']
                        lead['wa_link'] = phone_info['wa_link']
                        lead['enrichment_source'] = 'web_scraping'
                        lead['enrichment_date'] = now_wita()
                        logger.info(f"Enriched {lead.get('nama_bisnis', 'Unknown')}: {phone_info['formatted']}")
                    else:
                        lead['enrichment_source'] = 'web_scraping_failed'
                        lead['enrichment_date'] = now_wita()
                        logger.info("No valid WhatsApp number found")
                    
                    page.close()
                    
                except PlaywrightTimeout:
                    logger.warning(f"Timeout loading {url}")
                    lead['enrichment_source'] = 'web_scraping_timeout'
                    lead['enrichment_date'] = now_wita()
                except Exception as e:
                    logger.warning(f"Error scraping {url}: {e}")
                    lead['enrichment_source'] = 'web_scraping_error'
                    lead['enrichment_date'] = now_wita()
                
                enriched.append(lead)
            
            context.close()
            browser.close()
            
    except Exception as e:
        logger.error(f"Browser initialization error: {e}")
        # Append remaining leads without enrichment
        for lead, _ in leads_to_scrape:
            if lead not in enriched:
                lead['enrichment_source'] = 'browser_error'
                lead['enrichment_date'] = now_wita()
                enriched.append(lead)
    
    return enriched


# ─── 4. CLI INTERFACE ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="RUANG VISUAL Web Enricher - Extract WhatsApp from business websites"
    )
    parser.add_argument(
        '--url',
        type=str,
        help='Single URL to test scraping'
    )
    parser.add_argument(
        '--input',
        type=str,
        help='JSON file with leads to enrich (must have website field)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximum number of websites to scrape (default: 10)'
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
        logger.info(f"Testing single URL: {args.url}")
        result = scrape_website_for_whatsapp(args.url)
        if result:
            phone_info = classify_phone_number(result)
            print("\n--- Extraction Result ---")
            print(f"Raw Number: {result}")
            print(f"Formatted: {phone_info['formatted']}")
            print(f"WhatsApp Link: {phone_info['wa_link']}")
            print(f"Type: {phone_info['type']}")
        else:
            print("\nNo WhatsApp number found")
        return
    
    # Mode 2: Batch processing from JSON
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            logger.error(f"Input file not found: {args.input}")
            return
        
        with open(input_path, 'r', encoding='utf-8') as f:
            leads = json.load(f)
        
        logger.info(f"Loaded {len(leads)} leads from {args.input}")
        
        enriched_leads = enrich_leads_from_websites(leads, limit=args.limit)
        
        # Count enrichment success
        success_count = sum(1 for lead in enriched_leads if lead.get('enrichment_source') == 'web_scraping')
        logger.info(f"Enrichment complete: {success_count}/{len(enriched_leads)} leads enriched")
        
        if not args.dry_run:
            if args.output:
                output_path = Path(args.output)
            else:
                output_path = save_raw_json(enriched_leads, 'web_enricher')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(enriched_leads, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Results saved to: {output_path}")
        else:
            logger.info("Dry run mode: results not saved")
        
        return
    
    # No mode selected
    logger.error("Please specify --url for single test or --input for batch processing")
    parser.print_help()


if __name__ == "__main__":
    main()
