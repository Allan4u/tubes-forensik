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

# Setting Wireshark - FIXED: Gunakan 0.0.0.0 agar bisa capture
WIRESHARK_IP = "127.0.0.1"  # Target localhost
WIRESHARK_PORT = 9999
WIRESHARK_BIND_IP = "0.0.0.0"  # Bind ke semua interface

# Socket UDP untuk kirim ke Wireshark
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- DATABASE ---
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

# --- KIRIM KE WIRESHARK (FIXED) ---
def send_to_wireshark(status, app_name, details, risk=0):
    try:
        # Format payload dengan delimiter yang jelas untuk Wireshark
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Payload JSON agar mudah di-parse di Wireshark
        payload = {
            "timestamp": timestamp,
            "status": status,
            "app": app_name,
            "risk": risk,
            "details": details
        }
        
        # Kirim sebagai JSON string
        msg = json.dumps(payload)
        
        # Kirim paket UDP
        sock.sendto(msg.encode('utf-8'), (WIRESHARK_IP, WIRESHARK_PORT))
        
        # Debug print dengan warna
        color = "\033[96m"  # Cyan untuk network
        print(f"{color}[NETWORK] UDP → {WIRESHARK_IP}:{WIRESHARK_PORT} | {status[:30]}\033[0m")
        
    except Exception as e:
        print(f"\033[91m[NETWORK ERROR] {e}\033[0m")

# --- CALCULATE DREAD SCORE ---
def calculate_dread(event_type):
    """
    DREAD Scoring untuk setiap tipe event
    D = Damage potential (1-10)
    R = Reproducibility (1-10)
    E = Exploitability (1-10)
    A = Affected users (1-10)
    D = Discoverability (1-10)
    """
    dread_matrix = {
        "FAKE GPS DETECTED": {"D": 8, "R": 9, "E": 7, "A": 8, "Disc": 6},
        "USER USED FAKE GPS TO MAPS": {"D": 10, "R": 10, "E": 8, "A": 9, "Disc": 7},
        "ATTACKED": {"D": 9, "R": 10, "E": 9, "A": 7, "Disc": 8},
        "HIGH_FREQ_ACCESS": {"D": 7, "R": 10, "E": 8, "A": 6, "Disc": 9},
        "AMAN": {"D": 1, "R": 1, "E": 1, "A": 1, "Disc": 1},
    }
    
    scores = dread_matrix.get(event_type, {"D": 5, "R": 5, "E": 5, "A": 5, "Disc": 5})
    total = sum(scores.values())
    return total, scores

# --- LOG EVENT (FIXED) ---
def log_event(status, source, risk, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    
    # Hitung DREAD score
    dread_total, dread_detail = calculate_dread(status)
    
    # Warna Terminal
    color = "\033[97m"  # White default
    if status == "AMAN": 
        color = "\033[92m"  # Green
    elif "FAKE GPS DETECTED" in status: 
        color = "\033[93m"  # Yellow
    elif "USER USED FAKE" in status or status == "ATTACKED" or "HIGH_FREQ" in msg: 
        color = "\033[91m"  # Red
    
    # Print dengan DREAD score
    print(f"{color}[{ts}] {status} | {source} | Risk:{risk} | DREAD:{dread_total}/50 | {msg}\033[0m")
    
    # Simpan ke Database dengan DREAD
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO logs (timestamp, event, source, risk, msg, dread_score) VALUES (?, ?, ?, ?, ?, ?)",
                  (ts, status, source, risk, msg, dread_total))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")

    # Kirim ke Wireshark dengan detail lengkap
    details_full = f"{msg} | DREAD:{dread_total} | D:{dread_detail.get('D',0)} R:{dread_detail.get('R',0)} E:{dread_detail.get('E',0)} A:{dread_detail.get('A',0)} Disc:{dread_detail.get('Disc',0)}"
    send_to_wireshark(status, source, details_full, risk)

# --- ENGINE UTAMA (FIXED) ---
def start_engine():
    # Validasi ADB
    if not os.path.exists(ADB_PATH):
        print(f"\033[91m[ERROR] ADB tidak ditemukan di {ADB_PATH}\033[0m")
        print("Download dari: https://developer.android.com/studio/releases/platform-tools")
        return
    
    # Check ADB connection
    try:
        result = subprocess.run([ADB_PATH, 'devices'], capture_output=True, text=True)
        if "device" not in result.stdout:
            print("\033[91m[ERROR] Tidak ada device terkoneksi!\033[0m")
            print("Jalankan: adb connect <IP_EMULATOR>")
            return
    except Exception as e:
        print(f"\033[91m[ERROR] ADB check failed: {e}\033[0m")
        return

    init_db()
    
    print("\033[92m" + "="*70)
    print("🔥 LOCSHIELD TURBO ENGINE - FORENSIC MODE ACTIVATED 🔥")
    print("="*70 + "\033[0m")
    print(f"[NETWORK] Wireshark Target: {WIRESHARK_IP}:{WIRESHARK_PORT}")
    print(f"[NETWORK] Bind Interface: {WIRESHARK_BIND_IP}")
    print(f"[INFO] Untuk capture Wireshark:")
    print(f"       1. Buka Wireshark → Capture → Options")
    print(f"       2. Pilih interface 'Loopback' atau 'Adapter for loopback'")
    print(f"       3. Filter: udp.port == {WIRESHARK_PORT}")
    print(f"       4. Start Capture")
    print("\033[92m" + "="*70 + "\033[0m\n")
    
    # Start logcat
    cmd = [ADB_PATH, 'logcat', '-v', 'threadtime', '-T', '1']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                               text=True, encoding='utf-8', errors='ignore', bufsize=1)

    last_fake_pulse = 0
    last_gps_access = {}
    FAKE_KEYWORDS = ["fake", "mock", "lexa", "gpsjoystick", "flygps", "fakegps"]
    
    # Counter untuk metrik
    access_count = {}
    start_time = time.time()

    print("[ENGINE] Monitoring started... Press Ctrl+C to stop\n")

    try:
        while True:
            line = process.stdout.readline()
            if not line: 
                time.sleep(0.1)
                continue
                
            line_lower = line.lower()
            now = time.time()

            # 1. DETEKSI FAKE GPS (SPOOFING THREAT - STRIDE: S)
            if any(keyword in line_lower for keyword in FAKE_KEYWORDS):
                last_fake_pulse = now
                if any(x in line_lower for x in ["start", "service", "provider", "enabled"]):
                    log_event("FAKE GPS DETECTED", "System/Mock Provider", 9, 
                             "Mock Location Provider Active - STRIDE: Spoofing")

            # 2. DETEKSI GOOGLE MAPS (HIGH-VALUE TARGET)
            elif "com.google.android.apps.maps" in line_lower:
                if any(x in line_lower for x in ["location", "gps", "latitude", "longitude"]):
                    delta = now - last_fake_pulse
                    
                    # Update counter
                    app = "Google Maps"
                    access_count[app] = access_count.get(app, 0) + 1
                    
                    if delta < 15.0:  # Window 15 detik
                        log_event("USER USED FAKE GPS TO MAPS", app, 10, 
                                 f"SPOOFING ATTACK! Mock trace found {delta:.1f}s ago | Total Access: {access_count[app]}")
                    else:
                        # Rate limiting check
                        if app not in last_gps_access:
                            last_gps_access[app] = []
                        
                        last_gps_access[app].append(now)
                        # Keep only last 10 minutes
                        last_gps_access[app] = [t for t in last_gps_access[app] if now - t < 600]
                        
                        rate = len(last_gps_access[app])
                        if rate > 50:  # Lebih dari 50 akses dalam 10 menit
                            log_event("HIGH_FREQ_ACCESS", app, 7, 
                                     f"Excessive GPS access detected: {rate} times in 10 min | STRIDE: DoS")
                        else:
                            log_event("AMAN", app, 1, 
                                     f"Real GPS Access Verified | Rate: {rate}/10min")

            # 3. APLIKASI KITA (LocShield Agent)
            elif "LOCSHIELD_BRIDGE" in line:
                try:
                    json_part = line.split("LOCSHIELD_BRIDGE:")[1].strip()
                    # Clean any ANSI codes or extra characters
                    json_part = re.sub(r'\x1b\[[0-9;]*m', '', json_part)
                    
                    data = json.loads(json_part)
                    event_type = data.get('event', 'UNKNOWN')
                    
                    if data['risk'] >= 8:
                        status = "ATTACKED" if "THREAT" in event_type else "HIGH_RISK_EVENT"
                    elif data['risk'] >= 5:
                        status = "AUDIT"
                    else:
                        status = "INFO"
                    
                    log_event(status, data.get('source', 'LocShield'), 
                             data.get('risk', 0), data.get('msg', 'No message'))
                except json.JSONDecodeError as e:
                    print(f"\033[93m[JSON ERROR] Failed to parse: {e}\033[0m")
                except Exception as e:
                    print(f"\033[93m[PARSE ERROR] {e}\033[0m")

            # 4. DETEKSI APLIKASI LAIN YANG AKSES LOKASI
            elif "ACCESS_FINE_LOCATION" in line or "ACCESS_COARSE_LOCATION" in line:
                # Extract package name
                pkg_match = re.search(r'([a-z][a-z0-9_]*(\.[a-z0-9_]+)+)', line_lower)
                if pkg_match:
                    pkg = pkg_match.group(1)
                    if pkg not in ["com.google.android.gms", "com.android.systemui"]:
                        access_count[pkg] = access_count.get(pkg, 0) + 1
                        log_event("THIRD_PARTY_ACCESS", pkg, 5, 
                                 f"Location permission used | Total: {access_count[pkg]}")

    except KeyboardInterrupt:
        print("\n\033[92m[ENGINE] Shutting down gracefully...\033[0m")
        
        # Print summary
        elapsed = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"SESSION SUMMARY ({elapsed/60:.1f} minutes)")
        print(f"{'='*70}")
        for app, count in access_count.items():
            print(f"  {app}: {count} accesses")
        print(f"{'='*70}\n")
        
    finally:
        process.terminate()
        sock.close()

if __name__ == "__main__":
    try: 
        start_engine()
    except Exception as e:
        print(f"\033[91m[FATAL ERROR] {e}\033[0m")
        import traceback
        traceback.print_exc()