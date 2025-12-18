import socket
import json
from datetime import datetime

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('127.0.0.1', 9999))

print("\033[92m" + "="*70)
print("🎧 UDP LISTENER STARTED - Port 9999")
print("="*70 + "\033[0m")
print("Waiting for packets from engine.py...\n")

packet_count = 0

try:
    while True:
        # Receive data
        data, addr = sock.recvfrom(4096)
        packet_count += 1
        
        try:
            # Decode and parse JSON
            payload = json.loads(data.decode('utf-8'))
            
            # Color based on risk
            if payload['risk'] >= 8:
                color = "\033[91m"  # Red
            elif payload['risk'] >= 5:
                color = "\033[93m"  # Yellow
            else:
                color = "\033[92m"  # Green
            
            # Print formatted
            print(f"{color}[Packet #{packet_count}] {payload['timestamp']}")
            print(f"  Status: {payload['status']}")
            print(f"  App: {payload['app']}")
            print(f"  Risk: {payload['risk']}/10")
            print(f"  Details: {payload['details'][:80]}...")
            print("\033[0m")
            
        except json.JSONDecodeError:
            print(f"\033[91m[Error] Invalid JSON: {data[:100]}\033[0m")
        except Exception as e:
            print(f"\033[91m[Error] {e}\033[0m")

except KeyboardInterrupt:
    print(f"\n\033[92mStopped. Total packets received: {packet_count}\033[0m")
finally:
    sock.close()