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
WIRESHARK_IP = "127.0.0.1"
WIRESHARK_PORT = 9999
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- DATABASE ---
def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS logs')
        c.execute('''CREATE TABLE logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT, event TEXT, source TEXT, risk INTEGER, msg TEXT)''')
        conn.commit()
        conn.close()
    except: pass

# --- KIRIM KE WIRESHARK ---
def send_to_wireshark(status, app_name, details):
    try:
        msg = f"LOG_PACKET | {status} | {app_name} | {details}"
        sock.sendto(msg.encode('utf-8'), (WIRESHARK_IP, WIRESHARK_PORT))
    except: pass

def log_event(status, source, risk, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    color = "\033[97m" 
    if status == "AMAN": color = "\033[92m" 
    if status == "FAKE GPS DETECTED": color = "\033[93m" 
    if "USER USED FAKE" in status or status == "ATTACKED": color = "\033[91m"
    
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

# --- ENGINE UTAMA ---
def start_engine():
    if not os.path.exists(ADB_PATH):
        print(f"ERROR: ADB tidak ditemukan di {ADB_PATH}"); return

    init_db()
    print(f"[ENGINE] STABLE MODE ACTIVE (Memory: 10 Detik)")
    
    cmd = [ADB_PATH, 'logcat', '-v', 'threadtime']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')

    last_fake_pulse = 0
    # List kata kunci diperluas agar mendeteksi lebih banyak jenis Fake GPS
    FAKE_KEYWORDS = ["fake", "mock", "lexa", "gpsjoystick", "flygps", "locspoofer"]

    while True:
        line = process.stdout.readline()
        if not line: break
        line_lower = line.lower()
        now = time.time()

        # 1. DETEKSI FAKE GPS (DARI APLIKASI ATAU SISTEM)
        # Jika ada log apapun yang mengandung kata "fake", "mock", dll
        if any(x in line_lower for x in FAKE_KEYWORDS):
            # Kita anggap ini aktivitas Fake GPS
            last_fake_pulse = now
            
            # Opsional: Jika lognya jelas, kita catat
            if "start" in line_lower or "service" in line_lower or "provider" in line_lower:
                 log_event("FAKE GPS DETECTED", "System/App", 9, "Mock Activity Detected")

        # 2. DETEKSI GOOGLE MAPS
        elif "com.google.android.apps.maps" in line_lower:
            if "location" in line_lower or "gps" in line_lower:
                
                # Cek selisih waktu (DIPERPANJANG JADI 10 DETIK)
                delta = now - last_fake_pulse
                
                if delta < 10.0:
                    # Jika ada aktivitas Fake GPS dalam 10 detik terakhir -> BAHAYA
                    log_event("USER USED FAKE GPS TO MAPS", "Google Maps", 10, f"SPOOFING! (Trace found {delta:.1f}s ago)")
                else:
                    # Jika benar-benar bersih > 10 detik -> AMAN
                    log_event("AMAN", "Google Maps", 1, "Real GPS Access Verified")

        # 3. APLIKASI KITA (LocShield)
        elif "LOCSHIELD_BRIDGE" in line:
            try:
                data = json.loads(line.split("LOCSHIELD_BRIDGE:")[1].strip())
                status = "ATTACKED" if data['risk'] > 5 else "AUDIT"
                log_event(status, data['source'], data['risk'], data['msg'])
            except: pass

if __name__ == "__main__":
    try: start_engine()
    except KeyboardInterrupt: print("Stopped.")