import urllib.request
import json

API_BASE = "https://sekolah.data.kemendikdasmen.go.id"
CARI_ENDPOINT = f"{API_BASE}/v1/sekolah-service/sekolah/cari-sekolah"

def fetch(keyword, kabupaten_kota):
    payload = {
        "page": 1,
        "size": 5,
        "keyword": keyword,
        "kabupaten_kota": kabupaten_kota,
        "bentuk_pendidikan": "",
        "status_sekolah": "",
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(CARI_ENDPOINT, data=data_bytes, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except Exception as e:
        print(f"Error: {e}")
        return []

print("--- Test 1: Keyword 'Bandung', no filter ---")
results1 = fetch("Bandung", "")
for r in results1:
    print(f"Name: {r['nama']}, Kab: {r['kabupaten']}")

print("\n--- Test 2: Keyword '', Filter 'Kota Bandung' ---")
results2 = fetch("", "Kota Bandung")
for r in results2:
    print(f"Name: {r['nama']}, Kab: {r['kabupaten']}")

print("\n--- Test 3: Keyword 'Bandung', Filter 'Kab. Bandung' ---")
results3 = fetch("Bandung", "Kab. Bandung")
for r in results3:
    print(f"Name: {r['nama']}, Kab: {r['kabupaten']}")
