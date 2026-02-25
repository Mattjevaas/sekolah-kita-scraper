import urllib.request
import json
import ssl

# Ignore SSL errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

CARI_ENDPOINT = "https://sekolah.data.kemendikdasmen.go.id/v1/sekolah-service/sekolah/cari-sekolah"

def post_json(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
        return {}

# 1. Check raw data to see field name
print("Fetching raw data...")
raw = post_json(CARI_ENDPOINT, {"page": 0, "size": 10, "keyword": "", "kabupaten_kota": "Kota Bandung"})
if raw and raw.get('data'):
    print("Sample bentuk_pendidikan values:")
    for item in raw['data']:
        print(f"  - {item.get('bentuk_pendidikan')}")
else:
    print("No data found.")

# 2. Test filtering with single value
print("\nTesting filter: 'TK'")
tk_res = post_json(CARI_ENDPOINT, {"page": 0, "size": 5, "keyword": "", "kabupaten_kota": "Kota Bandung", "bentuk_pendidikan": "TK"})
count_tk = len(tk_res.get('data', []))
print(f"Returned {count_tk} items.")
if count_tk > 0:
    print(f"First item bentuk: {tk_res['data'][0].get('bentuk_pendidikan')}")

# 3. Test filtering with list (if supported)
print("\nTesting filter: ['TK', 'KB']")
multi_res = post_json(CARI_ENDPOINT, {"page": 0, "size": 5, "keyword": "", "kabupaten_kota": "Kota Bandung", "bentuk_pendidikan": ["TK", "KB"]})
count_multi = len(multi_res.get('data', []))
print(f"Returned {count_multi} items with list filter.")
if count_multi > 0:
    for item in multi_res['data']:
        print(f"  - {item.get('bentuk_pendidikan')}")

# 4. Test filtering with comma-separated string
print("\nTesting filter: 'TK,KB'")
comma_res = post_json(CARI_ENDPOINT, {"page": 0, "size": 5, "keyword": "", "kabupaten_kota": "Kota Bandung", "bentuk_pendidikan": "TK,KB"})
count_comma = len(comma_res.get('data', []))
print(f"Returned {count_comma} items with comma filter.")
