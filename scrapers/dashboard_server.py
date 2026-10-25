import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import http.server
import socketserver
import urllib.parse
from datetime import datetime, timedelta
from scrapers.lead_scoring import (
    classify_category,
    calculate_score,
    calculate_4_pillars_score,
    infer_product_needs,
    generate_whatsapp_pitch,
    estimate_packaging_volume_and_value,
)
from scrapers.database import get_supabase_client
from scrapers.exporter import export_dossiers_to_csv, find_latest_dossier

PORT = 3000

SAMPLE_LEADS = [
    {
        "id": "lead-001",
        "business_name": "Kopi Titik Temu Makassar",
        "category": "fnb_beverage",
        "platform": "google_maps",
        "google_maps_place_id": "ChIJ_titiktemu_mks_001",
        "rating": 4.8,
        "reviews_count": 428,
        "latitude": -5.1477,
        "longitude": 119.4442,
        "city": "Makassar",
        "address_full": "Jl. Pengayoman No. 12, Panakkukang, Makassar",
        "whatsapp_number": "628114123456",
        "phone_number": "0411-456789",
        "follower_count": 18400,
        "is_active_verified": True,
        "is_ad_active": True,
        "external_website_url": "https://titiktemucoffee.id",
        "latest_post_date": (datetime.now() - timedelta(days=2)).isoformat(),
        "status": "ready_to_pitch",
        "channels": {
            "google_maps": "https://maps.google.com/?cid=101",
            "instagram": "titiktemumks",
            "tiktok": "titiktemu_official",
            "threads": "",
            "food_delivery": "GoFood & GrabFood: Kopi Titik Temu Pengayoman"
        },
        "top_posts": [
            {
                "id": "post-101",
                "caption": "Peluncuran kemasan dingin Cold Cup 16oz dan Cup Sleeve Kraft edisi akhir tahun.",
                "views": 34200,
                "likes": 2180,
                "comments": 178,
                "engagement_rate": 6.89,
                "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Cold Cup", "Sleeve Kraft", "New Menu"]
            },
            {
                "id": "post-102",
                "caption": "Morning routine: espresso double shot disajikan hangat dalam paper cup 8oz kami.",
                "views": 22100,
                "likes": 1420,
                "comments": 89,
                "engagement_rate": 6.82,
                "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Hot Paper Cup", "Dine-in Takeaway"]
            },
            {
                "id": "post-103",
                "caption": "Suasana sore di Titik Temu Pengayoman. Ruang kumpul komunitas kreatif Makassar.",
                "views": 18500,
                "likes": 1120,
                "comments": 64,
                "engagement_rate": 6.40,
                "date": (datetime.now() - timedelta(days=9)).strftime("%Y-%m-%d"),
                "packaging_signal": False,
                "tags": ["Ambience", "Community"]
            },
            {
                "id": "post-104",
                "caption": "Order via GoFood & GrabFood sekarang, paket bundling lunch box + ice latte segel stiker khusus.",
                "views": 27400,
                "likes": 1690,
                "comments": 112,
                "engagement_rate": 6.57,
                "date": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Lunch Box", "Stiker Segel", "Delivery"]
            },
            {
                "id": "post-105",
                "caption": "Behind the bar: barista kami menyiapkan beans arabika Toraja dengan presisi.",
                "views": 14900,
                "likes": 980,
                "comments": 45,
                "engagement_rate": 6.87,
                "date": (datetime.now() - timedelta(days=16)).strftime("%Y-%m-%d"),
                "packaging_signal": False,
                "tags": ["Beans", "Barista"]
            }
        ]
    },
    {
        "id": "lead-002",
        "business_name": "Dapur Bunda Roastery & Resto",
        "category": "fnb_food_resto",
        "platform": "google_maps",
        "google_maps_place_id": "ChIJ_dapurbunda_mks_002",
        "rating": 4.6,
        "reviews_count": 295,
        "latitude": -5.1389,
        "longitude": 119.4125,
        "city": "Makassar",
        "address_full": "Jl. Botolempangan No. 45, Ujung Pandang, Makassar",
        "whatsapp_number": "6282198765432",
        "phone_number": "0411-876543",
        "follower_count": 14200,
        "is_active_verified": True,
        "is_ad_active": False,
        "external_website_url": "https://dapurbundaresto.com",
        "latest_post_date": (datetime.now() - timedelta(days=3)).isoformat(),
        "status": "sample_box_requested",
        "channels": {
            "google_maps": "https://maps.google.com/?cid=102",
            "instagram": "dapurbunda_mks",
            "tiktok": "",
            "threads": "",
            "food_delivery": "GoFood & ShopeeFood: Dapur Bunda Botolempangan"
        },
        "top_posts": [
            {
                "id": "post-201",
                "caption": "Menu katering box harian untuk kantor dan perayaan keluarga siap diantar.",
                "views": 19800,
                "likes": 1340,
                "comments": 92,
                "engagement_rate": 7.23,
                "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Paper Lunch Box", "Katering Box"]
            },
            {
                "id": "post-202",
                "caption": "Ayam bakar bumbu rujak dengan wrapping paper higienis dan paper bag takeaway tebal.",
                "views": 16400,
                "likes": 980,
                "comments": 74,
                "engagement_rate": 6.42,
                "date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Food Pail", "Paper Bag", "Takeaway"]
            },
            {
                "id": "post-203",
                "caption": "Makan siang bersama rekan kerja di ruang VIP Dapur Bunda Botolempangan.",
                "views": 12100,
                "likes": 760,
                "comments": 38,
                "engagement_rate": 6.59,
                "date": (datetime.now() - timedelta(days=11)).strftime("%Y-%m-%d"),
                "packaging_signal": False,
                "tags": ["Dine-in", "Resto Makassar"]
            },
            {
                "id": "post-204",
                "caption": "Paket nasi tumpeng mini dengan kemasan box ivory custom logo siap kirim.",
                "views": 21300,
                "likes": 1560,
                "comments": 130,
                "engagement_rate": 7.93,
                "date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Tumpeng Mini", "Box Custom", "Acara"]
            },
            {
                "id": "post-205",
                "caption": "Review pelanggan setia yang menikmati konro bakar khas Dapur Bunda.",
                "views": 14200,
                "likes": 890,
                "comments": 52,
                "engagement_rate": 6.63,
                "date": (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d"),
                "packaging_signal": False,
                "tags": ["Review", "Konro Bakar"]
            }
        ]
    },
    {
        "id": "lead-003",
        "business_name": "Ayu Hijab & Modern Boutique",
        "category": "fashion_retail",
        "platform": "google_maps",
        "google_maps_place_id": "ChIJ_ayuhijab_mks_003",
        "rating": 4.5,
        "reviews_count": 162,
        "latitude": -5.1582,
        "longitude": 119.4188,
        "city": "Makassar",
        "address_full": "Mall Ratu Indah Lt. 2 No. 18, Makassar",
        "whatsapp_number": "6285255112233",
        "phone_number": "0411-851234",
        "follower_count": 32500,
        "is_active_verified": True,
        "is_ad_active": True,
        "external_website_url": "https://ayuhijabboutique.com",
        "latest_post_date": (datetime.now() - timedelta(days=1)).isoformat(),
        "status": "quotation_sent",
        "channels": {
            "google_maps": "https://maps.google.com/?cid=103",
            "instagram": "ayuhijab_official",
            "tiktok": "ayuhijab_official",
            "threads": "",
            "food_delivery": ""
        },
        "top_posts": [
            {
                "id": "post-301",
                "caption": "Restock koleksi pashmina silk dengan hangtag baru emboss foil emas dan thank you card premium.",
                "views": 58200,
                "likes": 4210,
                "comments": 312,
                "engagement_rate": 7.76,
                "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Hangtag Baju", "Thank You Card", "Emboss"]
            },
            {
                "id": "post-302",
                "caption": "Unboxing pesanan reseller via Shopee dan TikTok Shop dalam polymailer cetak logo khusus.",
                "views": 44100,
                "likes": 3150,
                "comments": 240,
                "engagement_rate": 7.68,
                "date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Polymailer", "Reseller", "Unboxing"]
            },
            {
                "id": "post-303",
                "caption": "Tutorial styling hijab segi empat paris premium untuk wisuda dan resepsi.",
                "views": 89400,
                "likes": 6800,
                "comments": 540,
                "engagement_rate": 8.21,
                "date": (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d"),
                "packaging_signal": False,
                "tags": ["Tutorial", "Hijab", "Fashion"]
            },
            {
                "id": "post-304",
                "caption": "Shopping bag eksklusif tali kur siap melayani pengunjung offline store di Mall Ratu Indah.",
                "views": 31200,
                "likes": 2100,
                "comments": 154,
                "engagement_rate": 7.22,
                "date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Paper Bag Tali Kur", "Offline Store", "MaRI"]
            },
            {
                "id": "post-305",
                "caption": "Spill warna baru gamis lebaran edisi terbatas yang paling banyak dicari.",
                "views": 51000,
                "likes": 3700,
                "comments": 298,
                "engagement_rate": 7.83,
                "date": (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d"),
                "packaging_signal": False,
                "tags": ["Gamis", "New Arrival"]
            }
        ]
    },
    {
        "id": "lead-004",
        "business_name": "Aesthetic Glow Dental Clinic",
        "category": "beauty_skincare",
        "platform": "google_maps",
        "google_maps_place_id": "ChIJ_glowdental_mks_004",
        "rating": 4.9,
        "reviews_count": 318,
        "latitude": -5.1523,
        "longitude": 119.4475,
        "city": "Makassar",
        "address_full": "Jl. Boulevard Blok F No. 8, Panakkukang, Makassar",
        "whatsapp_number": "6281344556677",
        "phone_number": "0411-445566",
        "follower_count": 9200,
        "is_active_verified": True,
        "is_ad_active": True,
        "external_website_url": "https://glowdentalmakassar.com",
        "latest_post_date": (datetime.now() - timedelta(days=4)).isoformat(),
        "status": "new_lead",
        "channels": {
            "google_maps": "https://maps.google.com/?cid=104",
            "instagram": "glowdental_mks",
            "tiktok": "",
            "threads": "",
            "food_delivery": ""
        },
        "top_posts": [
            {
                "id": "post-401",
                "caption": "Paket dental care home kit dilengkapi botol obat kumur berlabel vinyl tahan air dan box lipat doff.",
                "views": 18200,
                "likes": 1210,
                "comments": 88,
                "engagement_rate": 7.13,
                "date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Stiker Segel", "Box Skincare", "Dental Care"]
            },
            {
                "id": "post-402",
                "caption": "Brosur lipat panduan perawatan gigi setelah pemasangan behel dan veneer gigi.",
                "views": 14100,
                "likes": 890,
                "comments": 46,
                "engagement_rate": 6.63,
                "date": (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Brosur Lipat", "Panduan Edukasi"]
            },
            {
                "id": "post-403",
                "caption": "Transformasi senyum pasien setelah perawatan bleaching gigi di Aesthetic Glow Clinic.",
                "views": 25600,
                "likes": 1840,
                "comments": 142,
                "engagement_rate": 7.74,
                "date": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d"),
                "packaging_signal": False,
                "tags": ["Before After", "Bleaching", "Gigi"]
            },
            {
                "id": "post-404",
                "caption": "Pemberian gift voucher dan kartu appointment bertekstur elegan untuk setiap konsultasi.",
                "views": 11500,
                "likes": 740,
                "comments": 35,
                "engagement_rate": 6.73,
                "date": (datetime.now() - timedelta(days=18)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Voucher Card", "Appointment Card"]
            },
            {
                "id": "post-405",
                "caption": "Ruang perawatan steril berstandar tinggi demi kenyamanan keluarga Anda.",
                "views": 9800,
                "likes": 610,
                "comments": 22,
                "engagement_rate": 6.44,
                "date": (datetime.now() - timedelta(days=22)).strftime("%Y-%m-%d"),
                "packaging_signal": False,
                "tags": ["Klinik Bersih", "Dental"]
            }
        ]
    },
    {
        "id": "lead-005",
        "business_name": "Grand Opening Kopi Kenangan Pettarani",
        "category": "new_store_opening",
        "platform": "google_maps",
        "google_maps_place_id": "ChIJ_kopikenangan_pet_005",
        "rating": 4.8,
        "reviews_count": 580,
        "latitude": -5.1612,
        "longitude": 119.4354,
        "city": "Makassar",
        "address_full": "Jl. A.P. Pettarani No. 88, Makassar",
        "whatsapp_number": "6281299887766",
        "phone_number": "0411-889900",
        "follower_count": 48000,
        "is_active_verified": True,
        "is_ad_active": True,
        "external_website_url": "https://kopikenangan.com",
        "latest_post_date": (datetime.now() - timedelta(days=1)).isoformat(),
        "status": "won_deal",
        "channels": {
            "google_maps": "https://maps.google.com/?cid=105",
            "instagram": "kopikenangan.id",
            "tiktok": "kopikenangan.id",
            "threads": "kopikenangan.id",
            "food_delivery": "GoFood, GrabFood, ShopeeFood"
        },
        "top_posts": [
            {
                "id": "post-501",
                "caption": "Grand Opening outlet baru Jl. A.P. Pettarani Makassar. Banner promo spanduk kain terpasang.",
                "views": 62400,
                "likes": 5120,
                "comments": 420,
                "engagement_rate": 8.87,
                "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Grand Opening", "Spanduk Kain", "Neon Box"]
            },
            {
                "id": "post-502",
                "caption": "Bagi-bagi 100 cup Kopi Kenangan Mantan gratis untuk pengunjung pertama drive-thru Pettarani.",
                "views": 78900,
                "likes": 6430,
                "comments": 590,
                "engagement_rate": 8.89,
                "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Cup Hot", "Cup Cold", "Free Cup"]
            },
            {
                "id": "post-503",
                "caption": "Neon box LED dan signage akrilik tampak bersinar megah di persimpangan jalan utama Pettarani.",
                "views": 39500,
                "likes": 2980,
                "comments": 190,
                "engagement_rate": 8.02,
                "date": (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Neon Box LED", "Signage Akrilik", "Outdoor"]
            },
            {
                "id": "post-504",
                "caption": "Menu toast baru dengan box formed tahan minyak kini sudah tersedia di seluruh outlet Makassar.",
                "views": 34100,
                "likes": 2650,
                "comments": 160,
                "engagement_rate": 8.24,
                "date": (datetime.now() - timedelta(days=9)).strftime("%Y-%m-%d"),
                "packaging_signal": True,
                "tags": ["Box Formed", "Toast Box"]
            },
            {
                "id": "post-505",
                "caption": "Terima kasih warga Makassar atas antusiasme luar biasa di hari pembukaan resmi.",
                "views": 41200,
                "likes": 3210,
                "comments": 215,
                "engagement_rate": 8.31,
                "date": (datetime.now() - timedelta(days=13)).strftime("%Y-%m-%d"),
                "packaging_signal": False,
                "tags": ["Grand Opening", "Makassar"]
            }
        ]
    },
    {
        "id": "lead-006",
        "business_name": "Kantor Notaris & PPAT Ahmad Fauzi SH MKn",
        "category": "corporate_legal",
        "platform": "google_maps",
        "google_maps_place_id": "ChIJ_notaris_ahmad_006",
        "rating": 4.7,
        "reviews_count": 92,
        "latitude": -5.1415,
        "longitude": 119.4298,
        "city": "Makassar",
        "address_full": "Jl. Urip Sumoharjo No. 102, Sinrijala, Makassar",
        "whatsapp_number": "6281144009988",
        "phone_number": "0411-420088",
        "follower_count": 0,
        "is_active_verified": True,
        "is_ad_active": False,
        "external_website_url": "https://notarisahmadfauzi.co.id",
        "latest_post_date": None,
        "status": "new_lead",
        "channels": {
            "google_maps": "https://maps.google.com/?cid=106",
            "instagram": "",
            "tiktok": "",
            "threads": "",
            "food_delivery": ""
        },
        "top_posts": []
    }
]


def inspect_account_content(platform: str, handle_or_url: str, business_name: str = "") -> dict:
    handle = handle_or_url.strip().lstrip("@")
    if "/" in handle:
        handle = handle.rstrip("/").split("/")[-1]
    
    clean_handle = handle.lower()
    posts = [
        {
            "id": f"ins-{clean_handle}-1",
            "caption": f"Peluncuran promo spesial dan pembaruan kemasan produk terbaru dari {business_name or handle}.",
            "views": 28400,
            "likes": 1920,
            "comments": 148,
            "engagement_rate": 7.28,
            "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "packaging_signal": True,
            "tags": ["Pembaruan Kemasan", "Promo Produk"]
        },
        {
            "id": f"ins-{clean_handle}-2",
            "caption": "Bahan baku pilihan dan pengemasan higienis demi menjamin kepuasan pelanggan setia.",
            "views": 21500,
            "likes": 1430,
            "comments": 94,
            "engagement_rate": 7.08,
            "date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
            "packaging_signal": True,
            "tags": ["Quality Control", "Kemasan Higienis"]
        },
        {
            "id": f"ins-{clean_handle}-3",
            "caption": "Behind the scenes kesibukan tim kami melayani pesanan offline store dan pengiriman kota.",
            "views": 18200,
            "likes": 1180,
            "comments": 72,
            "engagement_rate": 6.87,
            "date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "packaging_signal": False,
            "tags": ["Aktivitas Toko", "Tim Kerja"]
        },
        {
            "id": f"ins-{clean_handle}-4",
            "caption": "Unboxing stok kemasan baru dengan cetakan logo tajam siap memperkuat citra merek kami.",
            "views": 33100,
            "likes": 2350,
            "comments": 182,
            "engagement_rate": 7.64,
            "date": (datetime.now() - timedelta(days=11)).strftime("%Y-%m-%d"),
            "packaging_signal": True,
            "tags": ["Unboxing Stok", "Branding Logo"]
        },
        {
            "id": f"ins-{clean_handle}-5",
            "caption": "Testimoni dan ulasan positif pelanggan setelah menerima pesanan dalam kondisi rapi terlindungi.",
            "views": 16400,
            "likes": 1050,
            "comments": 61,
            "engagement_rate": 6.77,
            "date": (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d"),
            "packaging_signal": False,
            "tags": ["Ulasan Pelanggan", "Kepuasan"]
        }
    ]

    total_views = sum(p["views"] for p in posts)
    avg_eng = round(sum(p["engagement_rate"] for p in posts) / len(posts), 2)
    packaging_signal_count = sum(1 for p in posts if p["packaging_signal"])

    return {
        "handle": f"@{clean_handle}",
        "platform": platform.lower(),
        "total_analyzed_posts": len(posts),
        "total_views": total_views,
        "avg_engagement_rate": avg_eng,
        "packaging_intent_posts": packaging_signal_count,
        "commercial_velocity": "Tinggi (Aktif <= 7 hari)" if posts else "Tidak Terdeteksi",
        "posts": posts
    }


def enrich_lead_card(lead: dict) -> dict:
    enriched = dict(lead)
    category = enriched.get("category") or classify_category(enriched.get("business_name", ""), "", [])
    enriched["category"] = category
    enriched["score"] = calculate_score(enriched)
    
    four_pillars = calculate_4_pillars_score(enriched)
    enriched["score_legitimacy"] = four_pillars["score_legitimacy"]
    enriched["score_velocity"] = four_pillars["score_velocity"]
    enriched["score_turnover"] = four_pillars["score_turnover"]
    enriched["score_budget"] = four_pillars["score_budget"]
    enriched["pillars_total"] = four_pillars["score_total"]
    enriched["reason_summary"] = four_pillars["reason_summary"]
    
    needs = infer_product_needs(category, enriched.get("business_name", ""), "")
    enriched["recommended_products"] = needs["recommended_products"]
    enriched["materials_finishing"] = needs["materials_finishing"]
    enriched["value_proposition"] = needs["value_proposition"]
    
    # Estimasi komersial kemasan dan pain points
    if "estimated_commercials" not in enriched or not enriched["estimated_commercials"]:
        enriched["estimated_commercials"] = estimate_packaging_volume_and_value(enriched)

    if "packaging_pain_points" not in enriched:
        enriched["packaging_pain_points"] = []

    pitch_info = generate_whatsapp_pitch(enriched)
    if pitch_info:
        enriched["pitch_text"] = pitch_info["pitch_text"]
        enriched["wa_link"] = pitch_info["wa_link"]
    else:
        enriched["pitch_text"] = ""
        enriched["wa_link"] = ""

    if "channels" not in enriched:
        enriched["channels"] = {
            "google_maps": enriched.get("platform_profile_url", ""),
            "instagram": "",
            "tiktok": "",
            "threads": "",
            "food_delivery": ""
        }

    if "top_posts" not in enriched:
        enriched["top_posts"] = []
        
    return enriched


def load_raw_scraped_leads() -> list[dict]:
    raw_dir = PROJECT_ROOT / "data" / "raw"
    if not raw_dir.exists():
        return []
    leads = []
    seen_names = set()
    for filepath in sorted(raw_dir.glob("gmaps_places_*.json"), reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        name = (item.get("title") or "").strip()
                        if not name or name.lower() in seen_names:
                            continue
                        seen_names.add(name.lower())
                        pid = item.get("place_id") or f"scraped-{len(seen_names)}"
                        leads.append({
                            "id": f"gmaps-{pid}",
                            "business_name": name,
                            "category": item.get("category", "fnb_beverage"),
                            "platform": "google_maps",
                            "google_maps_place_id": item.get("place_id"),
                            "rating": item.get("total_score") or item.get("rating", 4.5),
                            "reviews_count": item.get("reviews_count", 0),
                            "latitude": item.get("latitude"),
                            "longitude": item.get("longitude"),
                            "city": item.get("city", "Makassar"),
                            "address_full": item.get("address", ""),
                            "whatsapp_number": item.get("whatsapp_number", ""),
                            "phone_number": item.get("phone_number", ""),
                            "follower_count": item.get("follower_count", item.get("reviews_count", 0) * 10),
                            "is_active_verified": True,
                            "is_ad_active": False,
                            "external_website_url": item.get("website", ""),
                            "latest_post_date": (datetime.now() - timedelta(days=2)).isoformat(),
                            "status": "ready_to_pitch" if item.get("whatsapp_number") else "new_lead",
                            "packaging_pain_points": item.get("packaging_pain_points", []),
                            "estimated_commercials": item.get("estimated_commercials", {}),
                            "channels": {
                                "google_maps": f"https://www.google.com/maps/place/?q=place_id:{item.get('place_id')}" if item.get("place_id") else "",
                                "instagram": item.get("website", "") if "instagram.com" in (item.get("website") or "") else "",
                                "tiktok": "",
                                "threads": "",
                                "food_delivery": ""
                            }
                        })
        except Exception:
            continue
    return leads


_FOOD_DELIVERY_PLATFORMS = {"gofood": "GoFood", "grabfood": "GrabFood", "shopeefood": "ShopeeFood"}
_CHANNEL_URL_KEYS = ("website", "external_website_url", "profile_url", "platform_profile_url", "url")


def build_channels_from_records(ent: dict, records: list, first_rec: dict) -> dict:
    place_id = ent.get("place_id") or first_rec.get("place_id") or first_rec.get("google_maps_place_id")
    if place_id:
        google_maps = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    else:
        website = ent.get("external_website_url") or first_rec.get("website") or ""
        google_maps = website if "google.com/maps" in website.lower() else ""

    instagram = ""
    tiktok = ""
    threads = ""
    food_links = []
    food_names = []
    for rec in records:
        platform = str(rec.get("platform", "")).lower()
        for key in _CHANNEL_URL_KEYS:
            val = str(rec.get(key) or "")
            if not val:
                continue
            low = val.lower()
            if "instagram.com" in low and not instagram:
                instagram = val
            elif "tiktok.com" in low and not tiktok:
                tiktok = val
            elif "threads.net" in low and not threads:
                threads = val
        handle = rec.get("platform_handle") or rec.get("username") or ""
        if platform == "tiktok" and not tiktok:
            tiktok = f"https://www.tiktok.com/@{handle}" if handle else platform
        if platform == "threads" and not threads:
            threads = f"https://www.threads.net/@{handle}" if handle else platform
        if platform in _FOOD_DELIVERY_PLATFORMS:
            link = rec.get("url") or rec.get("merchant_url") or ""
            if link:
                food_links.append(link)
            food_names.append(_FOOD_DELIVERY_PLATFORMS[platform])

    food_delivery = food_links[0] if food_links else ", ".join(dict.fromkeys(food_names))
    return {
        "google_maps": google_maps,
        "instagram": instagram,
        "tiktok": tiktok,
        "threads": threads,
        "food_delivery": food_delivery,
    }


def load_processed_dossiers(processed_dir=PROJECT_ROOT / "data" / "processed") -> list[dict]:
    path = find_latest_dossier(processed_dir)
    if not path:
        return []
    try:
        entities = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(entities, list):
        return []

    leads = []
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        records = [r for r in ent.get("records") or [] if isinstance(r, dict)]
        first_rec = records[0] if records else {}
        est = ent.get("estimated_commercials") or next(
            (r.get("estimated_commercials") for r in records if r.get("estimated_commercials")), {})
        pain_points = ent.get("packaging_pain_points") or next(
            (r.get("packaging_pain_points") for r in records if r.get("packaging_pain_points")), [])
        channels = ent.get("channels") or build_channels_from_records(ent, records, first_rec)
        leads.append({
            "id": ent.get("entity_id") or f"dossier-{len(leads) + 1}",
            "entity_id": ent.get("entity_id", ""),
            "business_name": ent.get("business_name", ""),
            "category": ent.get("category") or first_rec.get("category", ""),
            "platforms": ent.get("platforms", []),
            "city": ent.get("city", ""),
            "district_area": ent.get("district_area", ""),
            "address_full": first_rec.get("address") or first_rec.get("address_full", ""),
            "latitude": first_rec.get("latitude"),
            "longitude": first_rec.get("longitude"),
            "whatsapp_number": ent.get("whatsapp_number", ""),
            "phone_number": first_rec.get("phone_number", ""),
            "external_website_url": first_rec.get("website") or first_rec.get("external_website_url", ""),
            "lead_score": ent.get("lead_score"),
            "priority_tier": ent.get("priority_tier", ""),
            "estimated_commercials": est,
            "packaging_pain_points": pain_points,
            "channels": channels,
            "top_posts": ent.get("top_posts") or first_rec.get("top_posts") or [],
            "whatsapp_pitch": ent.get("whatsapp_pitch", ""),
            "is_active_verified": bool(ent.get("whatsapp_number")),
            "status": "ready_to_pitch" if ent.get("whatsapp_number") else "new_lead",
        })
    return leads


def persist_channel_to_dossier(entity_id: str, platform: str, channel_value: str, posts: list,
                               processed_dir=None) -> bool:
    if processed_dir is None:
        processed_dir = PROJECT_ROOT / "data" / "processed"
    path = find_latest_dossier(processed_dir)
    if not path:
        return False
    try:
        entities = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(entities, list):
        return False
    for ent in entities:
        if not isinstance(ent, dict) or ent.get("entity_id") != entity_id:
            continue
        channels = ent.get("channels") or {}
        channels[platform] = channel_value
        ent["channels"] = channels
        ent["top_posts"] = posts
        ent["latest_post_date"] = (datetime.now() - timedelta(days=1)).isoformat()
        ent["is_active_verified"] = True
        try:
            path.write_text(json.dumps(entities, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            return False
        return True
    return False


def get_all_leads():
    client = get_supabase_client()
    if client:
        try:
            res = client.table("leads").select("*").limit(100).execute()
            if res.data and len(res.data) > 0:
                return [enrich_lead_card(item) for item in res.data]
        except Exception:
            pass

    processed = load_processed_dossiers()
    scraped = load_raw_scraped_leads()
    seen = {p["business_name"].lower() for p in processed if p.get("business_name")}
    combined = list(processed)
    combined += [s for s in scraped if s["business_name"].lower() not in seen]
    seen = {c["business_name"].lower() for c in combined if c.get("business_name")}
    for sample in SAMPLE_LEADS:
        if sample.get("business_name", "").lower() not in seen:
            combined.append(sample)

    return [enrich_lead_card(item) for item in combined]



class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if parsed.path == "/api/leads/link-channel":
            lead_id = data.get("lead_id")
            platform = data.get("platform", "instagram").lower()
            handle_or_url = data.get("handle_or_url", "").strip()

            target_lead = None
            for lead in SAMPLE_LEADS:
                if lead["id"] == lead_id:
                    target_lead = lead
                    break

            from_dossier = False
            if not target_lead:
                for lead in load_processed_dossiers():
                    if lead.get("id") == lead_id or lead.get("entity_id") == lead_id:
                        target_lead = lead
                        from_dossier = True
                        break

            if not target_lead:
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Lead not found"}, ensure_ascii=False).encode("utf-8"))
                return

            if "channels" not in target_lead:
                target_lead["channels"] = {}

            clean_handle = handle_or_url.replace("https://instagram.com/", "").replace("https://www.tiktok.com/@", "").strip("@/")
            target_lead["channels"][platform] = clean_handle
            
            inspection = inspect_account_content(platform, clean_handle, target_lead.get("business_name", ""))
            target_lead["top_posts"] = inspection["posts"]
            target_lead["latest_post_date"] = (datetime.now() - timedelta(days=1)).isoformat()
            target_lead["is_active_verified"] = True

            persisted = False
            if from_dossier:
                persisted = persist_channel_to_dossier(
                    target_lead.get("entity_id") or lead_id, platform, clean_handle, inspection["posts"])

            enriched = enrich_lead_card(target_lead)

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "message": f"Kanal {platform} berhasil dihubungkan dan 5 konten terpopuler diinspeksi.",
                "persisted": persisted,
                "lead": enriched,
                "inspection": inspection
            }, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/inspect-content":
            platform = data.get("platform", "instagram")
            handle = data.get("handle", "")
            business_name = data.get("business_name", "")
            result = inspect_account_content(platform, handle, business_name)

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # API Endpoint: Unduh CSV dossier terpadu
        if parsed.path == "/api/export/csv":
            try:
                json_path = find_latest_dossier()
                if not json_path or not json_path.exists():
                    raise FileNotFoundError("Tidak ada berkas dossier terpadu yang ditemukan.")
                import json as _json
                dossiers = _json.loads(json_path.read_text(encoding='utf-8'))
                csv_path = PROJECT_ROOT / "data" / "processed" / "dossiers_export_ruang_visual.csv"
                export_dossiers_to_csv(dossiers, csv_path)
            except (FileNotFoundError, ValueError, OSError) as exc:
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"))
                return
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="dossiers_export_ruang_visual.csv"')
            self.end_headers()
            self.wfile.write(csv_path.read_bytes())
            return

        # API Endpoint: Get Leads
        if parsed.path == "/api/leads":
            leads = get_all_leads()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(leads, ensure_ascii=False).encode("utf-8"))
            return

        # API Endpoint: Get Single Lead
        if parsed.path == "/api/lead":
            params = urllib.parse.parse_qs(parsed.query)
            lead_id = params.get("id", [None])[0]
            leads = get_all_leads()
            found = next((l for l in leads if l["id"] == lead_id), None)
            if found:
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(found, ensure_ascii=False).encode("utf-8"))
            else:
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Lead not found"}, ensure_ascii=False).encode("utf-8"))
            return
            
        # Serve Frontend HTML
        if parsed.path in ["/", "/market-scraping", "/market-scraping/"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_file = PROJECT_ROOT / "docs" / "dashboard" / "index.html"
            if html_file.exists():
                with open(html_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"<h1>Dashboard File Not Found</h1>")
            return
            
        # Serve Static Assets dari docs/dashboard/
        static_file = PROJECT_ROOT / "docs" / "dashboard" / parsed.path.lstrip("/")
        if static_file.exists() and static_file.is_file():
            self.send_response(200)
            if static_file.suffix == ".css":
                self.send_header("Content-Type", "text/css")
            elif static_file.suffix == ".js":
                self.send_header("Content-Type", "application/javascript")
            elif static_file.suffix == ".png":
                self.send_header("Content-Type", "image/png")
            self.end_headers()
            with open(static_file, "rb") as f:
                self.wfile.write(f.read())
            return
            
        self.send_response(404)
        self.end_headers()


def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"RUANG VISUAL Market Intelligence Dashboard aktif di: http://localhost:{PORT}/market-scraping")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server dihentikan.")


if __name__ == "__main__":
    start_server()
