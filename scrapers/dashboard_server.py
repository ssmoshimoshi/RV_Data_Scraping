import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import http.server
import socketserver
import urllib.parse
from scrapers.lead_scoring import classify_category, calculate_score, infer_product_needs, generate_whatsapp_pitch
from scrapers.database import get_supabase_client

PORT = 3000

SAMPLE_LEADS = [
    {
        "id": "lead-001",
        "business_name": "Kopi Titik Temu Makassar",
        "category": "fnb_beverage",
        "platform": "google_maps",
        "platform_handle": "titiktemumks",
        "platform_profile_url": "https://maps.google.com/?cid=123",
        "whatsapp_number": "628114123456",
        "city": "Makassar",
        "address_full": "Jl. Pengayoman No. 12, Panakkukang, Makassar",
        "follower_count": 8400,
        "is_active_verified": True,
        "latest_post_date": "2026-10-23T10:00:00Z",
        "status": "ready_to_pitch"
    },
    {
        "id": "lead-002",
        "business_name": "Dapur Bunda Roastery & Resto",
        "category": "fnb_food_resto",
        "platform": "instagram",
        "platform_handle": "dapurbunda_mks",
        "platform_profile_url": "https://instagram.com/dapurbunda_mks",
        "whatsapp_number": "6282198765432",
        "city": "Makassar",
        "address_full": "Jl. Botolempangan No. 45, Ujung Pandang, Makassar",
        "follower_count": 14200,
        "is_active_verified": True,
        "latest_post_date": "2026-10-24T08:30:00Z",
        "status": "sample_box_requested"
    },
    {
        "id": "lead-003",
        "business_name": "Ayu Hijab & Modern Boutique",
        "category": "fashion_retail",
        "platform": "tiktok",
        "platform_handle": "@ayuhijab_official",
        "platform_profile_url": "https://tiktok.com/@ayuhijab_official",
        "whatsapp_number": "6285255112233",
        "city": "Makassar",
        "address_full": "Mall Ratu Indah Lt. 2 No. 18, Makassar",
        "follower_count": 32500,
        "is_active_verified": True,
        "latest_post_date": "2026-10-22T14:15:00Z",
        "status": "quotation_sent"
    },
    {
        "id": "lead-004",
        "business_name": "Aesthetic Glow Dental Clinic",
        "category": "beauty_skincare",
        "platform": "google_maps",
        "platform_handle": "glowdental_mks",
        "platform_profile_url": "https://maps.google.com/?cid=456",
        "whatsapp_number": "6281344556677",
        "city": "Makassar",
        "address_full": "Jl. Boulevard Blok F No. 8, Panakkukang, Makassar",
        "follower_count": 5200,
        "is_active_verified": True,
        "latest_post_date": "2026-10-21T09:00:00Z",
        "status": "new_lead"
    },
    {
        "id": "lead-005",
        "business_name": "Grand Opening Kopi Kenangan Pettarani",
        "category": "new_store_opening",
        "platform": "threads",
        "platform_handle": "kopikenangan.id",
        "platform_profile_url": "https://threads.net/@kopikenangan.id",
        "whatsapp_number": "6281299887766",
        "city": "Makassar",
        "address_full": "Jl. A.P. Pettarani No. 88, Makassar",
        "follower_count": 48000,
        "is_active_verified": True,
        "latest_post_date": "2026-10-24T06:00:00Z",
        "status": "won_deal"
    }
]


def enrich_lead_card(lead: dict) -> dict:
    enriched = dict(lead)
    category = enriched.get("category") or classify_category(enriched.get("business_name", ""), "", [])
    enriched["category"] = category
    enriched["score"] = calculate_score(enriched)
    
    needs = infer_product_needs(category, enriched.get("business_name", ""), "")
    enriched["recommended_products"] = needs["recommended_products"]
    enriched["materials_finishing"] = needs["materials_finishing"]
    enriched["value_proposition"] = needs["value_proposition"]
    
    pitch_info = generate_whatsapp_pitch(enriched)
    if pitch_info:
        enriched["pitch_text"] = pitch_info["pitch_text"]
        enriched["wa_link"] = pitch_info["wa_link"]
    else:
        enriched["pitch_text"] = ""
        enriched["wa_link"] = ""
        
    return enriched


def get_all_leads():
    client = get_supabase_client()
    if client:
        try:
            res = client.table("leads").select("*").limit(100).execute()
            if res.data and len(res.data) > 0:
                return [enrich_lead_card(item) for item in res.data]
        except Exception:
            pass
            
    return [enrich_lead_card(item) for item in SAMPLE_LEADS]


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # API Endpoint: Get Leads
        if parsed.path == "/api/leads":
            leads = get_all_leads()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(leads, ensure_ascii=False).encode("utf-8"))
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
