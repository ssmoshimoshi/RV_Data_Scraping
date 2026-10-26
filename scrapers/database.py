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
    key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        return None

    from supabase import create_client, Client
    return create_client(url, key)


def insert_lead(lead_data: dict, score: int = 0, dry_run: bool = False) -> Tuple[bool, str]:
    if dry_run:
        return True, f"[DRY RUN] Would save lead: {lead_data.get('business_name')}"

    client = get_supabase_client()
    if not client:
        return False, "SUPABASE_URL atau NEXT_PUBLIC_SUPABASE_ANON_KEY belum terkonfigurasi di .env"

    try:
        # Strictly read-only: no INSERT/UPDATE/DELETE operations
        return False, "Mode read-only: operasi INSERT/UPDATE/DELETE dilarang. Gunakan snapshot catalog lokal."

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
        return 0, "SUPABASE_URL atau NEXT_PUBLIC_SUPABASE_ANON_KEY belum terkonfigurasi di .env"

    return 0, "Mode read-only: operasi INSERT/UPDATE/DELETE/UPSERT dilarang. Gunakan snapshot catalog lokal."
