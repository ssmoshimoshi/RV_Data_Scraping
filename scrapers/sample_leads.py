import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timedelta

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

