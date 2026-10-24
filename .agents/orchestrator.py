import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import subprocess
import time
import re

KILO_BIN = Path("/Users/muhammadfanani/.antigravity-ide/extensions/kilocode.kilo-code-7.8.15-darwin-arm64/bin/kilo")
BACKLOG_FILE = PROJECT_ROOT / ".agents" / "tasks" / "backlog.json"
VENV_PYTHON = PROJECT_ROOT / "scrapers" / ".venv" / "bin" / "python"
EMOJI_PATTERN = re.compile(r'[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2b55\u200d\ufe0f]')


def load_backlog():
    if not BACKLOG_FILE.exists():
        return {"tasks": []}
    with open(BACKLOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_backlog(data):
    with open(BACKLOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def check_anti_slop_and_emoji(file_path: Path):
    if not file_path.exists():
        return False, f"File {file_path} not found"
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    emojis = EMOJI_PATTERN.findall(content)
    if emojis:
        return False, f"Emoji ditemukan pada {file_path.name}: {emojis}"
    
    # Syntax compile check
    res = subprocess.run([str(VENV_PYTHON), "-m", "py_compile", str(file_path)], capture_output=True, text=True)
    if res.returncode != 0:
        return False, f"Syntax error pada {file_path.name}: {res.stderr}"
    
    return True, "OK"


def run_tests():
    res = subprocess.run(
        [str(VENV_PYTHON), "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    return res.returncode == 0, res.stdout + res.stderr


def execute_kilo_task(task: dict, max_retries: int = 2):
    task_id = task["id"]
    title = task["title"]
    desc = task["description"]
    target_file = PROJECT_ROOT / task["target_file"]
    test_file = PROJECT_ROOT / task["test_file"]
    
    print(f"\n[ORCHESTRATOR] Memulai pengerjaan: {title} ({task_id})")
    
    prompt = (
        f"Instruksi Tugas untuk Kilo (Developer Specialist):\n"
        f"Gunakan skill 'anti-slop' dan 'ponytail' untuk efisiensi token maksimal.\n"
        f"Target: {task['target_file']}\n"
        f"Test: {task['test_file']}\n\n"
        f"Detail: {desc}\n\n"
        f"Ketentuan Wajib:\n"
        f"1. Bebas emoji/emoticon mutlak.\n"
        f"2. Sertakan unit test lengkap di {task['test_file']} dan pastikan sintaks valid.\n"
        f"3. Selesaikan langsung dengan kode paling ringkas dan siap pakai."
    )
    
    for attempt in range(1, max_retries + 1):
        print(f"[ORCHESTRATOR] Mengirim instruksi ke Kilo CLI (Percobaan {attempt}/{max_retries})...")
        cmd = [
            str(KILO_BIN),
            "run",
            prompt,
            "--auto"
        ]
        
        try:
            proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=180)
            print(f"[ORCHESTRATOR] Kilo selesai merespons. Memulai verifikasi otomatis...")
        except subprocess.TimeoutExpired:
            print(f"[ORCHESTRATOR WARNING] Kilo melebihi batas waktu 180 detik (timeout). Melakukan retry...")
            continue
        
        # 1. Cek file keberadaan & Anti-slop / Emoji
        ok_target, msg_target = check_anti_slop_and_emoji(target_file)
        if not ok_target:
            print(f"[AUDIT FAIL] {msg_target}")
            prompt = f"Perbaiki error pada {task['target_file']}: {msg_target}. Jangan gunakan emoji dan pastikan sintaks benar."
            continue
            
        ok_test, msg_test = check_anti_slop_and_emoji(test_file)
        if not ok_test:
            print(f"[AUDIT FAIL] {msg_test}")
            prompt = f"Perbaiki error pada {task['test_file']}: {msg_test}. Jangan gunakan emoji dan pastikan sintaks benar."
            continue
            
        # 2. Cek Unit Test Suite
        test_passed, test_log = run_tests()
        if not test_passed:
            print(f"[AUDIT FAIL] Unit test gagal. Log:\n{test_log}")
            prompt = f"Unit test gagal setelah pengerjaan {task['target_file']}. Berikut log error:\n{test_log}\nPerbaiki modul atau unit test agar 100% pass."
            continue
            
        print(f"[AUDIT SUCCESS] Seluruh kriteria dan unit test lolos untuk {title}!")
        return True
        
    return False


def main():
    print("=== RUANG VISUAL AUTONOMOUS AGENT ORCHESTRATOR ===")
    data = load_backlog()
    tasks = data.get("tasks", [])
    
    pending_tasks = [t for t in tasks if t["status"] == "pending"]
    if not pending_tasks:
        print("Tidak ada tugas pending di backlog. Sistem up-to-date.")
        return
        
    print(f"Ditemukan {len(pending_tasks)} tugas pending. Memulai eksekusi otomatis...\n")
    
    for task in pending_tasks:
        success = execute_kilo_task(task)
        if success:
            task["status"] = "completed"
            task["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_backlog(data)
            print(f"[STATUS] Tugas {task['id']} selesai dan dicatat ke backlog.")
        else:
            task["status"] = "failed"
            save_backlog(data)
            print(f"[STATUS] Tugas {task['id']} gagal setelah retry. Menjeda eksekusi.")
            break
            
    print("\n=== Seluruh antrean yang memenuhi syarat telah selesai diproses ===")


if __name__ == "__main__":
    main()
