import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None

# Pastikan path Android platform-tools selalu tersedia di environment
ANDROID_TOOLS = "/Users/muhammadfanani/Library/Android/sdk/platform-tools"
if ANDROID_TOOLS not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{ANDROID_TOOLS}:{os.environ.get('PATH', '')}"

DEFAULT_DEVICE_SERIAL = "B6BAJ7ZHA6SGD6HE"

from scrapers.biolink_resolver import resolve_biolink_whatsapp
from scrapers.db_sqlite import init_db, upsert_lead
from scrapers.normalizer import normalize_whatsapp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("android_scraper")

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+62|62|08)[0-9\-\s]{8,15}")


def parse_count_metric(val_str: Optional[str]) -> int:
    if not val_str:
        return 0
    clean = val_str.replace(",", "").strip().upper()
    try:
        if "M" in clean:
            return int(float(clean.replace("M", "")) * 1000000)
        elif "K" in clean:
            return int(float(clean.replace("K", "")) * 1000)
        return int(clean)
    except (ValueError, TypeError):
        return 0


def get_android_device(serial: Optional[str] = None) -> Any:
    if u2 is None:
        raise RuntimeError("Library uiautomator2 belum terinstal pada lingkungan ini.")
    target_serial = serial or DEFAULT_DEVICE_SERIAL
    logger.info(f"Menghubungkan ke perangkat: {target_serial}")
    try:
        return u2.connect(target_serial)
    except Exception as e:
        logger.warning(f"Koneksi ke serial spesifik gagal ({e}), mencoba auto-detect...")
        return u2.connect()


def ensure_device_ready(d: Any) -> bool:
    if u2 is None or d is None:
        return False
    try:
        if not d.info.get("screenOn", True):
            logger.info("Layar perangkat mati. Menyalakan layar...")
            d.screen_on()
            time.sleep(1)
            d.swipe(0.5, 0.8, 0.5, 0.2, 0.2)
            time.sleep(1)
        return True
    except Exception as e:
        logger.error(f"Gagal memeriksa status perangkat: {e}")
        return False


def extract_instagram_profile(d: u2.Device, username: str, timeout: int = 10) -> Dict[str, Any]:
    username_clean = username.strip().lstrip("@").strip("<>").strip().lower()
    logger.info(f"Membuka profil Instagram: {username_clean}")

    intent_cmd = (
        f'am start -a android.intent.action.VIEW '
        f'-d "instagram://user?username={username_clean}" com.instagram.android'
    )
    d.shell(intent_cmd)

    start_wait = time.time()
    profile_loaded = False
    while time.time() - start_wait < timeout:
        title_el = d(resourceId="com.instagram.android:id/action_bar_title")
        if title_el.exists:
            profile_loaded = True
            break
        if d(textContains="User not found").exists or d(textContains="Page not available").exists:
            logger.warning(f"Profil @{username_clean} tidak ditemukan atau dihapus.")
            return {"username": username_clean, "status": "not_found", "error": "User not found"}
        time.sleep(0.5)

    if not profile_loaded:
        logger.warning(f"Batas waktu tercapai saat memuat profil @{username_clean}")
        return {"username": username_clean, "status": "timeout", "error": "Loading timeout"}

    time.sleep(1.0)

    more_button = d(textContains="… more")
    if not more_button.exists:
        more_button = d(text="more")
    if more_button.exists:
        try:
            more_button.click()
            time.sleep(0.5)
        except Exception:
            pass

    fullname_el = d(resourceId="com.instagram.android:id/profile_header_full_name_above_vanity")
    if not fullname_el.exists:
        fullname_el = d(resourceId="com.instagram.android:id/profile_header_full_name")
    full_name = fullname_el.get_text().strip() if fullname_el.exists else ""

    category_el = d(resourceId="com.instagram.android:id/profile_header_business_category")
    business_category = category_el.get_text().strip() if category_el.exists else ""

    posts_el = d(resourceId="com.instagram.android:id/profile_header_familiar_post_count_value")
    posts_count = parse_count_metric(posts_el.get_text() if posts_el.exists else None)

    followers_el = d(resourceId="com.instagram.android:id/profile_header_familiar_followers_value")
    followers_count = parse_count_metric(followers_el.get_text() if followers_el.exists else None)

    following_el = d(resourceId="com.instagram.android:id/profile_header_familiar_following_value")
    following_count = parse_count_metric(following_el.get_text() if following_el.exists else None)

    address_el = d(resourceId="com.instagram.android:id/address_text")
    address_text = address_el.get_text().strip() if address_el.exists else ""

    xml_content = d.dump_hierarchy()
    root = ET.fromstring(xml_content)

    bio_lines = []
    website_url = ""
    ignored_texts = {
        "Posts", "posts", "Followers", "followers", "Following", "following",
        "Follow", "Following", "Message", "Shop", "See translation",
        full_name, business_category, address_text, username_clean
    }

    collecting_bio = False
    for node in root.iter("node"):
        res_id = node.attrib.get("resource-id", "")
        text = node.attrib.get("text", "").strip()
        cls = node.attrib.get("class", "")

        if "profile_header_business_category" in res_id or "profile_header_full_name" in res_id:
            collecting_bio = True
            continue
        if "profile_header_follow_button" in res_id or "button_container" in res_id or "address_text" in res_id:
            if "button_container" in res_id or "profile_header_follow_button" in res_id:
                collecting_bio = False

        if collecting_bio and text and "TextView" in cls:
            if text in ignored_texts:
                continue
            # Filter baris yang hanya berisi metrik angka atau label metrik
            if re.match(r"^[0-9,.]+[KMkm]?$", text):
                continue
            if address_text and text in address_text:
                continue
            if any(domain in text.lower() for domain in [".com", ".id", "linktr.ee", "desty.page", "taplink", "bit.ly", "wa.me", "http"]):
                if not website_url:
                    website_url = text
            else:
                if text not in bio_lines:
                    bio_lines.append(text)

    bio_full = "\n".join(bio_lines).strip()

    detected_phone = None
    phone_candidates = PHONE_REGEX.findall(bio_full)
    for cand in phone_candidates:
        norm = normalize_whatsapp(cand)
        if norm:
            detected_phone = norm
            break

    detected_email = None
    email_candidates = EMAIL_PATTERN.findall(bio_full)
    if email_candidates:
        detected_email = email_candidates[0]

    contact_modal_data = {}
    contact_btn = d(text="Contact")
    if not contact_btn.exists:
        contact_btn = d(text="Kontak")
    if not contact_btn.exists:
        contact_btn = d(description="Contact")

    if contact_btn.exists:
        logger.info("Tombol kontak ditemukan, membuka rincian kontak...")
        try:
            contact_btn.click()
            time.sleep(1.2)

            modal_xml = d.dump_hierarchy()
            modal_root = ET.fromstring(modal_xml)
            modal_texts = []
            for m_node in modal_root.iter("node"):
                m_text = m_node.attrib.get("text", "").strip()
                if m_text and m_text not in modal_texts:
                    modal_texts.append(m_text)

            for m_txt in modal_texts:
                if not detected_phone:
                    phone_match = PHONE_REGEX.search(m_txt)
                    if phone_match:
                        norm = normalize_whatsapp(phone_match.group(0))
                        if norm:
                            detected_phone = norm
                            contact_modal_data["phone_from_contact_button"] = norm
                if not detected_email:
                    email_match = EMAIL_PATTERN.search(m_txt)
                    if email_match:
                        detected_email = email_match.group(0)
                        contact_modal_data["email_from_contact_button"] = detected_email

            d.press("back")
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Gagal membaca popup kontak: {e}")
            try:
                d.press("back")
            except Exception:
                pass

    if website_url and not detected_phone:
        logger.info(f"Mengecek tautan biolink: {website_url}")
        resolved_wa = resolve_biolink_whatsapp(website_url)
        if resolved_wa:
            detected_phone = resolved_wa
            logger.info(f"Nomor WhatsApp ditemukan dari biolink: {resolved_wa}")

    highlights = []
    for h_node in root.iter("node"):
        res_id = h_node.attrib.get("resource-id", "")
        if "username" in res_id and "highlight" in h_node.attrib.get("content-desc", "").lower():
            txt = h_node.attrib.get("text", "").strip()
            if txt and txt not in highlights:
                highlights.append(txt)

    profile_data = {
        "platform": "instagram",
        "username": username_clean,
        "full_name": full_name,
        "business_category": business_category,
        "posts_count": posts_count,
        "followers_count": followers_count,
        "following_count": following_count,
        "address": address_text,
        "bio": bio_full,
        "website_url": website_url,
        "whatsapp_number": detected_phone,
        "email": detected_email,
        "is_wa_valid": 1 if detected_phone else 0,
        "highlights": highlights,
        "contact_modal_data": contact_modal_data,
        "scraped_at": datetime.now().isoformat()
    }

    return profile_data


def save_raw_output(data: Dict[str, Any], username: str) -> Path:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = RAW_DATA_DIR / f"android_instagram_{username}_{timestamp}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Data mentah disimpan di: {file_path}")
    return file_path


def persist_profile_to_db(data: Dict[str, Any]) -> bool:
    username = data.get("username", "")
    if not username:
        return False

    entity_id = f"ent_ig_{username}"
    entity_payload = {
        "entity_id": entity_id,
        "business_name": data.get("full_name") or username,
        "target_sector": data.get("business_category") or "General Business",
        "primary_service_pillar": "Komersial & Bisnis",
        "category_raw": data.get("business_category"),
        "whatsapp_number": data.get("whatsapp_number"),
        "phone_raw": data.get("whatsapp_number"),
        "is_wa_valid": data.get("is_wa_valid", 0),
        "is_commercial": 1,
        "locations": {
            "address_full": data.get("address"),
            "city": "makassar" if "makassar" in (data.get("address") or "").lower() else None
        },
        "digital_footprints": {
            "website_url": data.get("website_url"),
            "instagram_handle": username,
            "instagram_bio": data.get("bio"),
            "instagram_followers": data.get("followers_count", 0),
        }
    }

    try:
        init_db()
        return upsert_lead(entity_payload)
    except Exception as e:
        logger.error(f"Gagal menyimpan ke SQLite database: {e}")
        return False


def run_batch_scrape(
    usernames: List[str],
    device_serial: Optional[str] = None,
    delay_range: tuple = (3, 6),
    dry_run: bool = False
) -> List[Dict[str, Any]]:
    d = get_android_device(device_serial)
    if not ensure_device_ready(d):
        logger.error("Perangkat tidak siap untuk operasi scraping.")
        return []

    results = []
    total = len(usernames)
    logger.info(f"Memulai perayapan {total} profil Instagram pada perangkat Android...")

    for idx, user in enumerate(usernames, 1):
        clean_user = user.strip().lstrip("@")
        if not clean_user:
            continue

        logger.info(f"[{idx}/{total}] Memproses @{clean_user}")
        try:
            profile = extract_instagram_profile(d, clean_user)
            results.append(profile)

            save_raw_output(profile, clean_user)

            if not dry_run and profile.get("status") != "not_found":
                persisted = persist_profile_to_db(profile)
                if persisted:
                    logger.info(f"Data @{clean_user} berhasil diperbarui di SQLite.")

            if idx < total:
                sleep_sec = random.uniform(delay_range[0], delay_range[1])
                logger.info(f"Jeda manusia acak selama {sleep_sec:.1f} detik sebelum profil berikutnya...")
                time.sleep(sleep_sec)

        except Exception as e:
            logger.error(f"Terjadi kesalahan saat memproses @{clean_user}: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(description="RUANG VISUAL — Android Physical Device Scraper")
    parser.add_argument("--username", type=str, help="Username Instagram target tunggal")
    parser.add_argument("--usernames", type=str, help="Daftar username pisahkan dengan koma")
    parser.add_argument("--file", type=str, help="Berkas teks berisi daftar username")
    parser.add_argument("--device", type=str, help="Nomor seri perangkat ADB (opsional)")
    parser.add_argument("--limit", type=int, default=10, help="Batas maksimal profil yang dirayap")
    parser.add_argument("--dry-run", action="store_true", help="Jalankan ekstraksi tanpa menulis ke database SQLite")
    parser.add_argument("--mode", type=str, default="instagram", choices=["instagram", "tiktok"], help="Platform target")

    args = parser.parse_args()

    target_list = []
    if args.username:
        target_list.append(args.username)
    elif args.usernames:
        target_list.extend([u.strip() for u in args.usernames.split(",") if u.strip()])
    elif args.file:
        file_path = Path(args.file)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                target_list.extend([line.strip() for line in f if line.strip()])
        else:
            logger.error(f"Berkas {args.file} tidak ditemukan.")
            sys.exit(1)
    else:
        target_list = ["kopiteori", "ruangvisual.id"]

    if args.limit:
        target_list = target_list[:args.limit]

    logger.info(f"Menjalankan perayapan Android untuk {len(target_list)} akun (dry_run={args.dry_run})")
    results = run_batch_scrape(target_list, device_serial=args.device, dry_run=args.dry_run)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
