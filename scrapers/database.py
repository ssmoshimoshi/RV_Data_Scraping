import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
from datetime import datetime, timezone
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        return None
    
    from supabase import create_client, Client
    return create_client(url, key)


def insert_lead(lead_data: dict, score: int = 0, dry_run: bool = False) -> Tuple[bool, str]:
    if dry_run:
        return True, f"[DRY RUN] Would save lead: {lead_data.get('business_name')}"
    
    client = get_supabase_client()
    if not client:
        return False, "SUPABASE_URL atau SUPABASE_KEY belum terkonfigurasi di .env"
    
    try:
        # 1. Simpan ke tabel leads
        res = client.table("leads").insert(lead_data).execute()
        if not res.data:
            return False, "Gagal menyimpan data ke tabel leads"
        
        lead_id = res.data[0]["id"]
        
        # 2. Simpan skor ke tabel lead_insights
        insight_data = {
            "lead_id": lead_id,
            "lead_score": score,
            "qualification_notes": "Terkualifikasi via sistem skoring otomatis"
        }
        client.table("lead_insights").insert(insight_data).execute()
        
        # 3. Inisialisasi status di crm_outreach
        crm_data = {
            "lead_id": lead_id,
            "status": "ready_to_pitch" if score >= 75 else "new_lead"
        }
        client.table("crm_outreach").insert(crm_data).execute()
        
        return True, lead_id
    except Exception as e:
        return False, f"Database error: {str(e)}"


_UPSERT_KEYS = (
    'entity_id', 'business_name', 'category', 'city', 'whatsapp_number',
    'lead_score', 'priority_tier', 'estimated_monthly_units',
    'estimated_monthly_value_idr', 'packaging_pain_points',
    'whatsapp_pitch', 'platforms', 'updated_at',
)


def batch_upsert_dossiers(dossiers: list[dict], dry_run: bool = False) -> Tuple[int, str]:
    if dry_run:
        print(f"Mode dry-run: {len(dossiers)} dossier akan disinkronkan ke tabel leads.")
        return len(dossiers), "Mode dry-run: simulasi berhasil"

    client = get_supabase_client()
    if not client:
        return 0, "SUPABASE_URL atau SUPABASE_KEY belum terkonfigurasi di .env"

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for d in dossiers:
        row = {k: d.get(k) for k in _UPSERT_KEYS}
        if isinstance(row.get('platforms'), list):
            row['platforms'] = ','.join(row['platforms'])
        if isinstance(row.get('packaging_pain_points'), list):
            row['packaging_pain_points'] = '; '.join(row['packaging_pain_points'])
        row['updated_at'] = now
        rows.append(row)

    try:
        client.table("leads").upsert(
            rows,
            on_conflict="entity_id,whatsapp_number"
        ).execute()
        return len(rows), f"Berhasil upsert {len(rows)} dossier ke tabel leads."
    except Exception as e:
        return 0, f"Gagal upsert ke Supabase: {str(e)}"
