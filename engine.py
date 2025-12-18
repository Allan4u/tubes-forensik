import subprocess
import json
import sqlite3
import re
import threading
import time
import os
import socket
from datetime import datetime

# ==============================================================================
# KONFIGURASI SYSTEM
# ==============================================================================
ADB_PATH = r"C:\Users\pyjyu\AppData\Local\Android\Sdk\platform-tools\adb.exe"
DB_FILE = "locshield.db"

# Setting Wireshark
WIRESHARK_IP = "127.0.0.1"
WIRESHARK_PORT = 9999
WIRESHARK_BIND_IP = "0.0.0.0"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Daftar Aplikasi Cheat untuk dicek
FAKE_KEYWORDS = [
    "com.lexa.fakegps",             
    "com.theappninjas.gpsjoystick", 
    "com.fly.gps",
    "com.incorporateapps.fakegps"
]

# ==============================================================================
# DATABASE
# ==============================================================================
def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS logs')
        c.execute('''CREATE TABLE logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT, event TEXT, source TEXT, risk INTEGER, msg TEXT, 
                  dread_score INTEGER DEFAULT 0)''')
        conn.commit()
        conn.close()
        print("[DB] Database initialized successfully")
    except Exception as e:
        print(f"[DB ERROR] {e}")

# ==============================================================================
# NETWORK & LOGGING
# ==============================================================================
def send_to_wireshark(status, app_name, details, risk=0):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        payload = {
            "timestamp": timestamp,
            "status": status,
            "app": app_name,
            "risk": risk,
            "details": details
        }
        msg = json.dumps(payload)
        sock.sendto(msg.encode('utf-8'), (WIRESHARK_IP, WIRESHARK_PORT))
        
        color = "\033[96m"
        print(f"{color}[NETWORK] UDP -> {WIRESHARK_IP}:{WIRESHARK_PORT} | {status[:30]}\033[0m")
    except Exception as e:
        pass

def calculate_dread(event_type):
    dread_matrix = {
        "FAKE GPS DETECTED": {"D": 8, "R": 9, "E": 7, "A": 8, "Disc": 6},
        "USER USED FAKE GPS TO MAPS": {"D": 10, "R": 10, "E": 8, "A": 9, "Disc": 7},
        "ATTACKED": {"D": 9, "R": 10, "E": 9, "A": 7, "Disc": 8},
        "AMAN": {"D": 1, "R": 1, "E": 1, "A": 1, "Disc": 1},
    }
    
    if "THREAT" in event_type or "ATTACK" in event_type:
        scores = dread_matrix["ATTACKED"]
    else:
        scores = dread_matrix.get(event_type, {"D": 5, "R": 5, "E": 5, "A": 5, "Disc": 5})
    return sum(scores.values()), scores

def log_event(status, source, risk, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    dread_total, dread_detail = calculate_dread(status)
    
    color = "\033[97m"  # White
    if status == "AMAN": 
        color = "\033[92m"  # Hijau
    elif "FAKE GPS" in status: 
        color = "\033[93m"  # Kuning
    elif "ATTACK" in status or "THREAT" in status or risk >= 7: 
        color = "\033[91m"  # Merah
    
    print(f"{color}[{ts}] {status} | {source} | Risk:{risk} | DREAD:{dread_total}/50 | {msg}\033[0m")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO logs (timestamp, event, source, risk, msg, dread_score) VALUES (?, ?, ?, ?, ?, ?)",
                  (ts, status, source, risk, msg, dread_total))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

    details_full = f"{msg} | DREAD:{dread_total}"
    send_to_wireshark(status, source, details_full, risk)

# ==============================================================================
# HELPER: CEK PROSES AKTIF (AUTO-VERIFY)
# ==============================================================================
def check_is_process_running():
    """
    Fungsi ini melakukan double-check ke sistem Android.
    Mengembalikan True jika aplikasi Fake GPS masih jalan.
    """
    try:
        # ps -A mengambil semua proses yang jalan
        cmd = [ADB_PATH, 'shell', 'ps', '-A']
        # timeout 1 detik biar tidak bikin lag
        output = subprocess.run(cmd, capture_output=True, text=True, errors='ignore', timeout=1.0).stdout.lower()
        
        for app in FAKE_KEYWORDS:
            if app in output:
                return True # MASIH JALAN!
        return False # SUDAH MATI
    except:
        return False

# ==============================================================================
# ENGINE UTAMA
# ==============================================================================
def start_engine():
    if not os.path.exists(ADB_PATH):
        print(f"\033[91m[ERROR] ADB tidak ditemukan di {ADB_PATH}\033[0m")
        return
    
    try:
        subprocess.run([ADB_PATH, 'devices'], capture_output=True)
    except:
        pass

    init_db()
    
    print("\033[92m" + "="*70)
    print("🔥 LOCSHIELD TURBO ENGINE - AUTO VERIFY MODE ACTIVATED 🔥")
    print("="*70 + "\033[0m")
    print(f"[INFO] System will auto-verify if Fake GPS is killed.")
    
    # --- VARIABEL STATE ---
    IS_FAKE_GPS_ACTIVE = False 
    last_verify_time = 0 

    # 1. STARTUP SCAN
    print("[ENGINE] Startup Scan...")
    if check_is_process_running():
        IS_FAKE_GPS_ACTIVE = True
        log_event("FAKE GPS DETECTED", "Startup Scan", 9, "Cheat App Found Running in Background!")
    else:
        print("[INFO] Clean startup. No cheats found.")

    # 2. MONITORING
    subprocess.run([ADB_PATH, 'logcat', '-c']) 
    
    cmd = [ADB_PATH, 'logcat', '-v', 'threadtime']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                               text=True, encoding='utf-8', errors='ignore', bufsize=1)

    print("[ENGINE] Monitoring started... (Realtime)\n")

    try:
        while True:
            line = process.stdout.readline()
            if not line: 
                continue 
                
            line_lower = line.lower()
            now = time.time()

            # --- A. DETEKSI LOG FAKE GPS ---
            # Jika log muncul, pasti aktif
            if any(keyword in line_lower for keyword in FAKE_KEYWORDS):
                if any(x in line_lower for x in ["start", "service", "provider", "enabled"]):
                    if not IS_FAKE_GPS_ACTIVE:
                        log_event("FAKE GPS DETECTED", "System Monitor", 9, "Mock Location ACTIVATED")
                    IS_FAKE_GPS_ACTIVE = True

            # --- B. TOMBOL ATTACK ---
            elif "LOCSHIELD_BRIDGE" in line:
                try:
                    json_start = line.find('{')
                    if json_start != -1:
                        json_str = line[json_start:].strip()
                        json_str = re.sub(r'\x1b\[[0-9;]*m', '', json_str)
                        data = json.loads(json_str)
                        risk = data.get('risk', 0)
                        event = data.get('event', '')
                        
                        if risk >= 8 or "THREAT" in event:
                            status = "ATTACKED"
                        elif "AUDIT" in event:
                            status = "AUDIT"
                        else:
                            status = "INFO"
                        
                        log_event(status, data.get('source', 'LocShield'), risk, data.get('msg', ''))
                except:
                    pass

            # --- C. GOOGLE MAPS (DENGAN AUTO-VERIFY) ---
            elif "com.google.android.apps.maps" in line_lower:
                if any(x in line_lower for x in ["location", "gps", "latitude", "longitude"]):
                    
                    # LOGIC BARU: Jika status ACTIVE, kita cek ulang benarkah masih jalan?
                    # Kita throttle cek ulang tiap 2 detik biar ga berat
                    if IS_FAKE_GPS_ACTIVE and (now - last_verify_time > 2.0):
                        is_still_running = check_is_process_running()
                        last_verify_time = now
                        
                        if not is_still_running:
                            # TAHU-TAHU MATI? Reset status!
                            IS_FAKE_GPS_ACTIVE = False
                            log_event("INFO", "System Monitor", 1, "Fake GPS Process Disappeared (Normalized)")

                    # LOGGING BERDASARKAN HASIL VERIFIKASI
                    if IS_FAKE_GPS_ACTIVE:
                        log_event("USER USED FAKE GPS TO MAPS", "Google Maps", 10, 
                                 "SPOOFING ATTACK! Accessing Maps while FakeGPS Process is RUNNING")
                    else:
                        log_event("AMAN", "Google Maps", 1, "Real GPS Access Verified (System Clean)")

    except KeyboardInterrupt:
        print("\n\033[92m[ENGINE] Shutting down...\033[0m")
    finally:
        process.terminate()
        sock.close()

if __name__ == "__main__":
    start_engine()