# 🛡️ LocShield: Mobile Location Privacy & Forensic System

**LocShield** adalah sistem keamanan mobile yang dirancang untuk mendeteksi anomali pada fitur lokasi Android, memitigasi serangan *GPS Spoofing*, dan melakukan analisis forensik jaringan secara *real-time*. Proyek ini menggabungkan agen Android, mesin deteksi berbasis Python, dan integrasi Wireshark.

![Status](https://img.shields.io/badge/Status-Completed-brightgreen) ![Python](https://img.shields.io/badge/Python-3.x-blue) ![Android](https://img.shields.io/badge/Platform-Android-green)

---

## 🛠 Prasyarat

Sebelum menjalankan sistem, pastikan lingkungan pengembangan Anda memiliki:

* **Python 3.x** terinstal.
* **Android Studio & Emulator** (dengan Mode Developer Aktif).
* **ADB (Android Platform Tools)** sudah ditambahkan ke Path sistem.
* **Wireshark** (terinstal dengan Npcap Loopback Adapter).
* **Library Python:**

```bash
pip install streamlit pandas plotly pysqlite3