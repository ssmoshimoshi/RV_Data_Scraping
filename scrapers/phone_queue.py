import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("phone_queue")
QUEUE_FILE = PROJECT_ROOT / "data" / "phone_queue.json"


def get_queue_file_path() -> Path:
    return QUEUE_FILE


def load_queue() -> Dict[str, Any]:
    if not QUEUE_FILE.exists():
        return {
            "updated_at": datetime.now().isoformat(),
            "queue": []
        }
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"updated_at": datetime.now().isoformat(), "queue": []}
            if "queue" not in data or not isinstance(data["queue"], list):
                data["queue"] = []
            return data
    except Exception as e:
        logger.error(f"Gagal membaca phone_queue.json: {e}")
        return {
            "updated_at": datetime.now().isoformat(),
            "queue": []
        }


def save_queue(queue_data: Dict[str, Any]) -> bool:
    try:
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        queue_data["updated_at"] = datetime.now().isoformat()
        temp_file = QUEUE_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)
        temp_file.replace(QUEUE_FILE)
        return True
    except Exception as e:
        logger.error(f"Gagal menyimpan phone_queue.json: {e}")
        return False


def add_to_queue(lead_id: str, business_name: str, platform: str, handle: str) -> Dict[str, Any]:
    data = load_queue()
    clean_handle = handle.strip().lstrip("@")
    
    # Cek apakah sudah ada di antrean yang masih pending atau processing
    for item in data["queue"]:
        if item.get("handle") == clean_handle and item.get("platform") == platform:
            if item.get("status") in ("pending", "processing"):
                return item

    new_item = {
        "id": f"q_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}",
        "lead_id": lead_id,
        "business_name": business_name,
        "platform": platform,
        "handle": clean_handle,
        "status": "pending",
        "added_at": datetime.now().isoformat(),
        "processed_at": None,
        "error_message": None
    }
    data["queue"].append(new_item)
    save_queue(data)
    return new_item


def get_pending_items() -> List[Dict[str, Any]]:
    data = load_queue()
    return [item for item in data.get("queue", []) if item.get("status") == "pending"]


def update_item_status(queue_id: str, status: str, error_message: Optional[str] = None) -> bool:
    data = load_queue()
    updated = False
    for item in data.get("queue", []):
        if item.get("id") == queue_id:
            item["status"] = status
            item["processed_at"] = datetime.now().isoformat()
            if error_message:
                item["error_message"] = error_message
            updated = True
            break
    if updated:
        save_queue(data)
    return updated


def clear_completed_items() -> int:
    data = load_queue()
    initial_count = len(data.get("queue", []))
    data["queue"] = [item for item in data.get("queue", []) if item.get("status") in ("pending", "processing")]
    removed = initial_count - len(data["queue"])
    if removed > 0:
        save_queue(data)
    return removed
