import subprocess
import json
import sqlite3
import re
import threading
import time
import os
import socket
from datetime import datetime

# --- KONFIGURASI ---
ADB_PATH = r"C:\Users\pyjyu\AppData\Local\Android\Sdk\platform-tools\adb.exe"
DB_FILE = "locshield.db"

# Wireshark
WIRESHARK_IP = "127.0.0.1"
WIRESHARK_PORT = 9999
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS logs')
    c.execute('''CREATE TABLE logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT, event TEXT, source TEXT, risk INTEGER, msg TEXT)''')
    conn.commit()
    conn.close()

def send_to_wireshark(status, app_name, details):
    try:
        payload = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "ALERT_STATUS": status,
            "APP_SOURCE": app_name,
            "DETAILS": details
        }
        sock.sendto(json.dumps(payload).encode('utf-8'), (WIRESHARK_IP, WIRESHARK_PORT))
    except: pass

def log_event(status, source, risk, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    
    color = "\033[97m" 
    if status == "AMAN": color = "\033[92m" # Hijau
    if status == "FAKE GPS DETECTED": color = "\033[93m" # Kuning
    if "USER USED FAKE" in status or status == "ATTACKED": color = "\033[91m" # Merah
    
    print(f"{color}[{ts}] {status} | {source} | {msg}\033[0m")

    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO logs (timestamp, event, source, risk, msg) VALUES (?, ?, ?, ?, ?)",
                  (ts, status, source, risk, msg))
        conn.commit()
        conn.close()
    except: pass

    send_to_wireshark(status, source, msg)

# --- FITUR BARU: CEK PROSES AKTIF (REAL TIME) ---
def is_fake_gps_running():
    """
    Fungsi ini mengecek apakah ada aplikasi Fake GPS yang SEDANG BERJALAN saat ini juga.
    Tidak pakai timer, tapi cek langsung ke RAM Android.
    """
    try:
        # Perintah 'ps -A' melist semua aplikasi yang jalan
        cmd = [ADB_PATH, 'shell', 'ps', '-A']
        # Gunakan subprocess.run agar cepat
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout.lower()
        
        # Cek apakah ada nama paket mencurigakan di daftar proses
        suspects = ["com.lexa.fakegps", "fake.gps", "mock", "newapphorizons"]
        
        for suspect in suspects:
            if suspect in output:
                return True, suspect # KETEMU! Ada Fake GPS jalan!
                
        return False, None
    except:
        return False, None

def start_engine():
    if not os.path.exists(ADB_PATH):
        print(f"ERROR: ADB tidak ditemukan di {ADB_PATH}"); return

    init_db()
    print(f"[ENGINE] REAL-TIME PROCESS MONITORING ACTIVE...")
    print("Metode: Active Process Scan (Tanpa Timer)")
    
    cmd = [ADB_PATH, 'logcat', '-v', 'threadtime']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')

    while True:
        line = process.stdout.readline()
        if not line: break
        line_lower = line.lower()

        # 1. DETEKSI SERANGAN (LocShield App)
        if "LOCSHIELD_BRIDGE" in line:
            try:
                data = json.loads(line.split("LOCSHIELD_BRIDGE:")[1].strip())
                status = "ATTACKED" if data['risk'] > 5 else "AUDIT"
                log_event(status, data['source'], data['risk'], data['msg'])
            except: pass

        # 2. DETEKSI FAKE GPS (Log Aktivitas)
        elif "com.lexa.fakegps" in line_lower or "fake.gps" in line_lower:
            if "start" in line_lower or "location" in line_lower:
                log_event("FAKE GPS DETECTED", "FakeGPS App", 9, "Active in Background")

        # 3. DETEKSI GOOGLE MAPS (DENGAN ACTIVE SCAN)
        elif "com.google.android.apps.maps" in line_lower:
            if "location" in line_lower or "gps" in line_lower:
                
                # --- CEK STATE SAAT INI JUGA ---
                is_running, app_name = is_fake_gps_running()
                
                if is_running:
                    # JIKA FAKE GPS NYALA DETIK INI -> BAHAYA
                    log_event("USER USED FAKE GPS TO MAPS", "Google Maps", 10, f"Spoofing Active! ({app_name} is running)")
                else:
                    # JIKA FAKE GPS MATI DETIK INI -> AMAN
                    log_event("AMAN", "Google Maps", 1, "Verified Secure Access")

        # 4. Mock Provider System
        elif "mock provider" in line_lower:
             log_event("FAKE GPS DETECTED", "Android System", 10, "System Mocking Active")

if __name__ == "__main__":
    try: start_engine()
    except KeyboardInterrupt: print("Stopped.")